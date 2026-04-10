import os
import cv2
import math
import torch
import pickle
import argparse
import numpy as np
from tqdm import tqdm
from glob import glob
import face_alignment
from threading import Thread
from queue import Queue


def load_args(args):
    parser = argparse.ArgumentParser()
    parser.add_argument("--root-dir", type=str, default="")
    parser.add_argument("--video-dir", type=str, default="videos")
    parser.add_argument("--fdata-dir", type=str, default="frame_data")
    parser.add_argument("--glob-exp", type=str, default="*/*")
    parser.add_argument("--split-num", type=int, default=1)
    parser.add_argument("--part-num", type=int, default=1)
    parser.add_argument("--batch", type=int, default=256, help="Batch size for processing frames. Larger batch reduces GPU idle time.")
    parser.add_argument("--max-res", type=int, default=800)
    args = parser.parse_args(args)

    assert args.part_num > 0 and args.split_num > 0, "split and part value should be > 0"

    args.part_num = args.part_num - 1

    return args


def read_video_frames(org_path, max_res):
    """Read all frames from video and return frames and scale factor.
    Optimized for speed: batch resize and color conversion."""
    cap_org = cv2.VideoCapture(org_path)
    # Try to use hardware acceleration backend if available
    try:
        # Try different backends for faster decoding
        backend = cv2.CAP_FFMPEG
        cap_org.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    except:
        pass
    
    try:
        width = int(cap_org.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap_org.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # determine the scaling factor to shrink the size of input image(for efficiency).
        if (max(height, width) > max_res):
            scale = max_res / max(height, width)
            new_width = int(width * scale)
            new_height = int(height * scale)
            need_resize = True
        else:
            scale = 1
            new_width = width
            new_height = height
            need_resize = False

        # Read all frames first, then process in batch (faster)
        raw_frames = []
        while True:
            ret, frame = cap_org.read()
            if not ret:
                break
            raw_frames.append(frame)
        
        if len(raw_frames) == 0:
            return [], scale
        
        # Batch process: convert color and resize together (much faster)
        if need_resize:
            # Convert all frames to RGB and resize in one go
            frames = []
            for frame in raw_frames:
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frame_resized = cv2.resize(frame_rgb, (new_width, new_height), interpolation=cv2.INTER_LINEAR)
                frames.append(frame_resized)
        else:
            # Only convert color space
            frames = [cv2.cvtColor(frame, cv2.COLOR_BGR2RGB) for frame in raw_frames]
        
        return frames, scale
    finally:
        cap_org.release()


@torch.inference_mode()
def landmark_extract(fn, frames, scale, batch_size):
    """Extract landmarks from pre-loaded frames."""
    frame_count = len(frames)
    if frame_count == 0:
        return []
        
    frame_faces = [None for _ in range(frame_count)]
    
    # Process in larger batches to reduce GPU idle time
    for batch_start in range(0, frame_count, batch_size):
        batch_end = min(batch_start + batch_size, frame_count)
        batch_frames = frames[batch_start:batch_end]
        batch_indices = list(range(batch_start, batch_end))

        # Convert to tensor and move to GPU in one go (more efficient)
        # Use contiguous array for faster transfer
        batch_array = np.ascontiguousarray(np.stack(batch_frames).transpose((0, 3, 1, 2)), dtype=np.float32)
        batch_tensor = torch.from_numpy(batch_array).cuda(non_blocking=True)

        results = fn(batch_tensor)

        batch_landmarks = results[0]
        batch_bboxes = results[2]

        # Process all results in batch to reduce overhead
        for frame_idx, frame_landmarks, frame_bboxes in zip(batch_indices, batch_landmarks, batch_bboxes):
            if (len(frame_landmarks) > 0):
                # Convert to numpy if tensor (batch convert for efficiency)
                if torch.is_tensor(frame_landmarks):
                    frame_landmarks = frame_landmarks.cpu().numpy()
                
                # Reshape and scale in one operation
                frame_landmarks = (frame_landmarks.reshape(-1, 68, 2) / scale).tolist()
                
                # Convert bboxes
                if len(frame_bboxes) > 0:
                    if torch.is_tensor(frame_bboxes[0]):
                        frame_bboxes = [bbox.cpu().numpy() for bbox in frame_bboxes]
                    frame_bboxes = [(bbox[:-1] / scale).tolist() for bbox in frame_bboxes]
                
                frame_faces[frame_idx] = {
                    "landmarks": frame_landmarks,
                    "bboxes": frame_bboxes
                }

    return frame_faces


def main(args=None):
    # This file extract video landmarks from a given folder.
    # In addition, the landmarks are tracked with landmarks from previous frames.
    # By doing so, we expect to extract the most consistently appeared faces from a given video.
    # Note that under 'pack' save mode, the extracted faces must match the length of the video.
    # That's to say, if there exists a single frame without appearing faces in the video, the extract operation fails.

    args = load_args(args=args)

    model = face_alignment.FaceAlignment(
        face_alignment.LandmarksType.TWO_D,
        face_detector='sfd',
        dtype=torch.float16,  # float16 to boost efficiency.
        flip_input=False,
        device="cuda",
    )

    def driver(x): return model.get_landmarks_from_batch(x, return_bboxes=True)
    
    def get_output_path(video_path, video_dir, fdata_dir, video_ext):
        """Generate output pickle path from video path."""
        if video_dir and video_dir.strip():
            # Replace video_dir with fdata_dir in the path
            lm_path = video_path.replace(video_dir, fdata_dir)
        else:
            # If video_dir is empty, insert fdata_dir before the filename
            dir_name = os.path.dirname(video_path)
            file_name = os.path.basename(video_path)
            lm_path = os.path.join(dir_name, fdata_dir, file_name)
        
        # Replace extension with .pickle
        lm_path = os.path.splitext(lm_path)[0] + '.pickle'
        return lm_path

    if (not args.root_dir[-1] == "/"):
        args.root_dir += "/"
    
    # Handle empty or whitespace-only video_dir
    if not args.video_dir or not args.video_dir.strip():
        args.video_dir = ""
        search_path = os.path.join(args.root_dir, args.glob_exp)
    else:
        args.video_dir = args.video_dir.strip()
        search_path = os.path.join(args.root_dir, args.video_dir, args.glob_exp)
    
    video_files = sorted(glob(search_path))
    
    if len(video_files) == 0:
        print(f"Error: No video files found matching pattern: {search_path}")
        print(f"Please check your --root-dir, --video-dir, and --glob-exp parameters.")
        return
    
    _, video_ext = os.path.splitext(video_files[0])

    # splitting
    split_size = math.ceil(len(video_files) / args.split_num)
    video_files = video_files[args.part_num * split_size:(args.part_num + 1) * split_size]
    n_videos = len(video_files)

    print("{} videos in {}".format(n_videos, args.root_dir))
    print("path sample:{}".format(video_files[0]))
    # Show output path sample
    sample_output = get_output_path(video_files[0], args.video_dir, args.fdata_dir, video_ext)
    print("output path sample:{}".format(sample_output))

    cont = input(f"Processing Part {args.part_num+1}/{args.split_num}, Confirm?(y/n)")
    if (not cont.lower() == "y"):
        print("abort.")
        return

    # Prefetch queue for pipeline processing (CPU reads next video while GPU processes current)
    prefetch_queue = Queue(maxsize=2)  # Allow 2 videos in queue for better pipelining
    prefetch_thread = None
    next_video_idx = 0
    
    def prefetch_worker(video_path, max_res):
        """Worker thread to prefetch video frames."""
        try:
            frames, scale = read_video_frames(video_path, max_res)
            prefetch_queue.put((frames, scale, True))
        except Exception as e:
            prefetch_queue.put((None, None, False))
    
    # Start prefetching first video immediately
    for i in tqdm(range(n_videos)):
        lm_path = get_output_path(video_files[i], args.video_dir, args.fdata_dir, video_ext)

        if (os.path.exists(lm_path)):
            # Still prefetch next video even if current is skipped
            if i + 1 < n_videos:
                next_lm_path = get_output_path(video_files[i + 1], args.video_dir, args.fdata_dir, video_ext)
                if not os.path.exists(next_lm_path):
                    if prefetch_thread is None or not prefetch_thread.is_alive():
                        prefetch_thread = Thread(target=prefetch_worker, args=(video_files[i + 1], args.max_res))
                        prefetch_thread.start()
                        next_video_idx = i + 1
            continue

        # Start prefetching next video early (before processing current)
        if i + 1 < n_videos and next_video_idx <= i:
            next_lm_path = get_output_path(video_files[i + 1], args.video_dir, args.fdata_dir, video_ext)
            if not os.path.exists(next_lm_path):
                if prefetch_thread is None or not prefetch_thread.is_alive():
                    prefetch_thread = Thread(target=prefetch_worker, args=(video_files[i + 1], args.max_res))
                    prefetch_thread.start()
                    next_video_idx = i + 1
        
        # Get current video frames: use prefetched data if available, otherwise read now
        frames, scale = None, None
        if not prefetch_queue.empty():
            frames, scale, success = prefetch_queue.get()
            if not success or frames is None:
                frames, scale = None, None
        
        if frames is None:
            # No prefetch available or prefetch failed, read now
            frames, scale = read_video_frames(video_files[i], args.max_res)
        
        # Process with GPU (GPU works here while next video is being prefetched)
        datas = landmark_extract(
            fn=driver,
            frames=frames,
            scale=scale,
            batch_size=args.batch
        )

        os.makedirs(os.path.split(lm_path)[0], exist_ok=True)
        with open(lm_path, "wb") as f:
            pickle.dump(datas, f)
        
        # Start prefetching next video while saving current result
        if i + 2 < n_videos and next_video_idx <= i + 1:
            next_next_lm_path = get_output_path(video_files[i + 2], args.video_dir, args.fdata_dir, video_ext)
            if not os.path.exists(next_next_lm_path):
                if prefetch_thread is None or not prefetch_thread.is_alive():
                    prefetch_thread = Thread(target=prefetch_worker, args=(video_files[i + 2], args.max_res))
                    prefetch_thread.start()
                    next_video_idx = i + 2
    
    # Wait for last prefetch thread to finish
    if prefetch_thread is not None and prefetch_thread.is_alive():
        prefetch_thread.join()


if __name__ == '__main__':
    main()
