from .base import *
from torchvision.io import read_image


class WDF(DeepFakeDataset):
    TYPE_DIRS = {
        'REAL': 'real_test',
        'FAKE': 'fake_test'
    }

    FRAME_EXTS = ('.png', '.jpg', '.jpeg')

    def __init__(self, *args, **kargs):
        super().__init__(*args, **kargs)
        if self.split != "test":
            raise ValueError("WDF only supports the test split with frame sequences.")
        self._build_video_table()
        self._build_video_list()

    @classmethod
    def prepare_data(cls, data_dir, *_, **__):
        # frame sequences are read directly; keep a lightweight existence check only.
        for df_type, df_dir in cls.TYPE_DIRS.items():
            target_dir = path.join(data_dir, df_dir)
            if not path.isdir(target_dir):
                logging.warning(f"WDF {df_type} directory missing: {target_dir}")

    @staticmethod
    def _frame_key(frame_path):
        stem = path.splitext(path.basename(frame_path))[0]
        try:
            return int(stem)
        except ValueError:
            return stem

    def _discover_tracks(self, root_dir, inner_dir):
        tracks = []
        if not path.isdir(root_dir):
            return tracks
        for subject in scandir(root_dir):
            if not subject.is_dir():
                continue
            candidate = path.join(subject.path, inner_dir)
            if not path.isdir(candidate):
                continue
            for track in scandir(candidate):
                if track.is_dir():
                    tracks.append(track.path)
        return tracks

    def _build_video_table(self):
        self.video_table = {}
        for df_type, df_dir in self.TYPE_DIRS.items():
            track_table = {}
            tracks = self._discover_tracks(
                path.join(self.data_dir, df_dir),
                df_type.lower()
            )
            for track_dir in tracks:
                frame_paths = [
                    f.path for f in scandir(track_dir)
                    if f.is_file() and f.name.lower().endswith(self.FRAME_EXTS)
                ]
                frame_paths = sorted(frame_paths, key=self._frame_key)
                if len(frame_paths) == 0:
                    continue
                track_name = path.relpath(track_dir, self.data_dir)
                track_table[track_name] = {
                    "path": track_dir,
                    "frames": frame_paths
                }

            if len(track_table) == 0:
                logging.warning(f"No valid tracks found under {df_dir}.")
            self.video_table[df_type] = track_table

    def _build_video_list(self):
        self.video_list = []

        for df_type in self.TYPE_DIRS:

            _videos = []

            for name in sorted(self.video_table[df_type].keys()):
                _videos.append((df_type.upper(), name, 1))

            self.video_list += _videos[:int(len(_videos) * self.ratio)]

        # permanant shuffle
        random.Random(1019).shuffle(self.video_list)

        # stacking up the amount of data clips for further usage
        self.stack_video_clips = [0]
        for _, _, i in self.video_list:
            self.stack_video_clips.append(self.stack_video_clips[-1] + i)
        self.stack_video_clips.pop(0)

    def __len__(self):
        if (self.pack):
            return len(self.video_list)
        else:
            return self.stack_video_clips[-1] if len(self.stack_video_clips) else 0

    def __getitem__(self, idx):
        item_entities = self.get_item(idx)
        return [[entity[k] for entity in item_entities] for k in item_entities[0].keys()]

    def get_item(self, idx, with_entity_info=False):
        item_entities = [
            self.get_entity(
                idx,
                with_entity_info=with_entity_info
            )
        ]
        return item_entities

    def get_entity(self, idx, with_entity_info=False):
        video_idx, df_type, video_name, _ = self.video_info(idx)
        video_meta = self.video_table[df_type][video_name]
        logging.debug(f"Entity/Video Index:{idx}/{video_idx}")
        logging.debug(f"Entity DF:{df_type}")

        # - video path
        vid_path = video_meta["path"]
        frame_paths = video_meta["frames"][:self.num_frames]

        entity_clips = []
        entity_masks = []

        # sequence-level test: single clip per track
        clips_desire = [0]

        for _ in clips_desire:
            frames = [read_image(f) for f in frame_paths]
            if len(frames) == 0:
                raise RuntimeError(f"No valid frames found in track: {vid_path}")

            # stack list of torch frames to tensor
            frames = torch.stack(frames)

            # transformation: prefer batched TCHW, fallback to per-frame if needed
            try:
                frames = self.transform(frames)
            except Exception as e:
                logging.debug(f"WDF fallback to per-frame transform due to: {e}")
                frames = torch.stack([self.transform(frame) for frame in frames])

            # padding and masking missing frames.
            mask = torch.tensor(
                [1.] * len(frame_paths) +
                [0.] * (self.num_frames - len(frame_paths)),
                dtype=torch.bool
            )
            if frames.shape[0] < self.num_frames:
                diff = self.num_frames - len(frames)
                padding = torch.zeros(
                    (diff, *frames.shape[1:]),
                    dtype=frames.dtype
                )
                frames = torch.cat([frames, padding], dim=0)

            entity_clips.append(frames)
            entity_masks.append(mask)

        entity_clips = torch.stack(entity_clips)
        entity_masks = torch.stack(entity_masks)

        entity_info = {
            "video_name": video_name,
            "df_type": df_type,
            "vid_path": vid_path
        }
        entity_data = {
            "clips": entity_clips,
            "label": 0 if (df_type == "REAL") else 1,
            "masks": entity_masks,
            "idx": idx
        }

        if with_entity_info:
            return {**entity_data, **entity_info}
        else:
            return entity_data

    def video_info(self, idx):
        if (self.pack):
            video_idx = idx
        else:
            video_idx = next(i for i, x in enumerate(self.stack_video_clips) if idx < x)
        return video_idx, *self.video_list[video_idx]

    def video_repr(self, idx):
        return '/'.join([str(i) for i in self.video_info(idx)[1:-1]])

    def video_meta(self, idx):
        df_type, name = self.video_info(idx)[1:3]
        return self.video_table[df_type][name]


class WDFDataModule(DeepFakeDataModule):
    def __init__(
        self,
        *args,
        **kargs
    ):
        super().__init__(*args, **kargs)

    def prepare_data(self):
        WDF.prepare_data(self.data_dir)

    def setup(self, stage: str):
        # Assign train/val datasets for use in dataloaders
        data_cls = partial(
            WDF,
            data_dir=self.data_dir,
            vid_ext=self.vid_ext,
            num_frames=self.num_frames,
            clip_duration=self.clip_duration,
            transform=self.transform,
            ratio=self.ratio,
            split="test",
            pack=self.pack
        )

        if (stage in {"fit", "valid", "train", "validate"}):
            raise RuntimeError("WDFDataModule supports test-only evaluation with frame sequences.")
        elif (stage in {"test", "predict", None}):
            dataset = data_cls()
            self._test_dataset = dataset
            self._predict_dataset = dataset


if __name__ == "__main__":
    from src.utility.visualize import dataset_entity_visualize

    class Dummy():
        pass

    dtm = WDFDataModule(
        data_dir="datasets/wdf/",
        vid_ext=".png",
        batch_size=1,
        num_workers=0,
        num_frames=10,
        clip_duration=1,
        ratio=1.0,
        pack=True
    )

    model = Dummy()
    model.transform = lambda x: x
    dtm.prepare_data()
    dtm.affine_model(model)
    dtm.setup("test")

    # iterate the whole dataset for visualization and sanity check
    iterable = dtm._test_dataset
    save_folder = f"./misc/extern/dump_dataset/wdf/test/"
    # entity dump
    for entity_idx in tqdm(range(len(iterable))):
        if (entity_idx > 100):
            break
        dataset_entity_visualize(iterable.get_entity(entity_idx, with_entity_info=True), base_dir=save_folder)

    # # single dump
    # dataset_entity_visualize(iterable.get_entity(167, with_entity_info=True), base_dir=save_folder)

    # iterate the all dataloaders for debugging.
    for fn in [dtm.val_dataloader, dtm.test_dataloader]:
        iterable = fn()
        for batch in tqdm(iterable):
            pass
