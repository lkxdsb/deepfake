from .base import *


class TTDF(DeepFakeDataset):
    """
    Dataset for the TT-DF layout:
    data_dir/
        REAL/videos/*.mp4
        FAKE/{animateAnyone,magicAnimate,magicDance}/videos/*.mp4
    """

    FAKE_METHODS = ("animateAnyone", "magicAnimate", "magicDance")
    TYPE_DIRS = {
        "REAL": "REAL/videos",
        "FAKE": {m: f"FAKE/{m}/videos" for m in FAKE_METHODS}
    }

    @classmethod
    def prepare_data(cls, data_dir, vid_ext, fake_methods=None):
        fake_methods = fake_methods or cls.FAKE_METHODS
        targets = [("REAL", "REAL")] + [("FAKE", m) for m in fake_methods]
        progress_bar = tqdm(targets)
        for df_type, method in progress_bar:
            progress_bar.set_description(f"{df_type}/{method}")
            meta_cache_path = path.expanduser(cls.get_cache_dir(df_type, method))
            if path.exists(meta_cache_path):
                continue

            if df_type == "REAL":
                video_dir = path.join(data_dir, cls.TYPE_DIRS["REAL"])
            else:
                rel_dir = cls.TYPE_DIRS["FAKE"].get(method)
                if rel_dir is None:
                    logging.warning(f"Skip unknown fake method: {method}")
                    continue
                video_dir = path.join(data_dir, rel_dir)

            if not path.isdir(video_dir):
                logging.warning(f"Missing video folder: {video_dir}")
                continue

            video_metas = cls.build_metadata(data_dir, video_dir, vid_ext)

            makedirs(path.dirname(meta_cache_path), exist_ok=True)
            with open(meta_cache_path, "wb") as f:
                pickle.dump(video_metas, f)

    def __init__(self, fake_methods=None, *args, **kargs):
        super().__init__(*args, **kargs)
        self.fake_methods = fake_methods or self.FAKE_METHODS
        self._build_video_table()
        self._build_video_list()

    def _load_split_csv(self):
        csv_path = path.join(self.data_dir, "csv_files", f"{self.split}.csv")
        if not path.exists(csv_path):
            return None
        df = pd.read_csv(csv_path)
        required_cols = {"filepath", "label"}
        if not required_cols.issubset(set(df.columns)):
            raise ValueError(f"CSV {csv_path} must contain columns: {required_cols}")
        return df

    def _build_video_table(self):
        self.video_table = {"REAL": {}, "FAKE": {}}

        def _load_cache(df_type, method):
            cache_path = path.expanduser(self.get_cache_dir(df_type, method))
            if not path.exists(cache_path):
                logging.warning(f"Metadata cache missing: {cache_path}")
                return {}
            with open(cache_path, "rb") as f:
                metas = pickle.load(f)
            for idx in metas:
                rel_path = metas[idx]["path"].lstrip("/\\")
                metas[idx]["path"] = path.join(self.data_dir, rel_path) + self.vid_ext
            return metas

        # real
        self.video_table["REAL"] = _load_cache("REAL", "REAL")

        # fake
        for method in self.fake_methods:
            self.video_table["FAKE"][method] = _load_cache("FAKE", method)

    def _build_video_list(self):
        self.video_list = []
        split_df = self._load_split_csv()

        candidates = []
        if split_df is not None:
            for row in split_df.itertuples(index=False):
                rel_fp = str(row.filepath)
                label = int(row.label)
                df_type = "REAL" if label == 0 else "FAKE"
                method = "REAL" if df_type == "REAL" else rel_fp.split(path.sep)[1]
                name = path.splitext(path.basename(rel_fp))[0]
                candidates.append((df_type, method, name, rel_fp))
        else:
            # consume all cached videos
            for name in self.video_table["REAL"]:
                candidates.append(("REAL", "REAL", name, None))
            for method, metas in self.video_table["FAKE"].items():
                for name in metas:
                    candidates.append(("FAKE", method, name, None))

        for df_type, method, name, rel_fp in candidates:
            meta_pool = self.video_table[df_type] if df_type == "REAL" else self.video_table["FAKE"].get(method, {})
            if name in meta_pool:
                meta = meta_pool[name]
                clips = int(meta["duration"] // self.clip_duration)
                if clips > 0:
                    clips = min(clips, self.max_clips)
                    self.video_list.append((df_type, method, name, clips))
            else:
                missing_name = rel_fp if rel_fp else f"{df_type}/{method}/{name}"
                logging.warning(f"Video missing in metadata: {missing_name}")
                self.stray_videos[missing_name] = 0 if df_type == "REAL" else 1

        random.Random(1019).shuffle(self.video_list)

        self.stack_video_clips = [0]
        for _, _, _, num_clips in self.video_list:
            self.stack_video_clips.append(self.stack_video_clips[-1] + num_clips)
        self.stack_video_clips.pop(0)

    def __len__(self):
        if self.pack:
            return len(self.video_list)
        return self.stack_video_clips[-1] if len(self.stack_video_clips) else 0

    def __getitem__(self, idx):
        item_entities = self.get_item(idx)
        return [[entity[k] for entity in item_entities] for k in item_entities[0].keys()]

    def get_item(self, idx, with_entity_info=False):
        return [
            self.get_entity(
                idx,
                with_entity_info=with_entity_info
            )
        ]

    def get_entity(self, idx, with_entity_info=False):
        video_idx, df_type, method, video_name, num_clips = self.video_info(idx)
        meta_pool = self.video_table[df_type] if df_type == "REAL" else self.video_table["FAKE"][method]
        video_meta = meta_pool[video_name]
        logging.debug(f"Entity/Video Index:{idx}/{video_idx}")
        logging.debug(f"Entity DF:{df_type}/{method}")

        vid_path = video_meta["path"]
        vid_reader = VideoReader(vid_path, "video")
        video_sample_freq = vid_reader.get_metadata()["video"]["fps"][0]

        entity_clips = []
        entity_masks = []

        if self.pack:
            clips_desire = range(num_clips)
        else:
            clips_desire = [idx - (0 if video_idx == 0 else self.stack_video_clips[video_idx - 1])]

        for clip_of_video in clips_desire:
            frames = []
            video_offset_duration = clip_of_video * self.clip_duration
            video_sample_offset = int(video_offset_duration)
            video_clip_samples = int(video_sample_freq * self.clip_duration)
            video_sample_stride = 0 if self.num_frames == 1 else ((video_clip_samples - 1) / (self.num_frames - 1)) / video_sample_freq

            logging.debug(f"Loading Video: {vid_path}")
            logging.debug(f"Sample Offset: {video_sample_offset}")
            logging.debug(f"Sample Stride: {video_sample_stride}")

            for sample_idx in range(self.num_frames):
                vid_reader.seek(video_sample_offset + sample_idx * video_sample_stride)
                frame = next(vid_reader)
                frames.append(frame["data"])

            frames = torch.stack(frames)
            frames = self.transform(frames)

            mask = torch.tensor(
                [1.] * len(frames) +
                [0.] * (self.num_frames - len(frames)),
                dtype=torch.bool
            )
            if frames.shape[0] < self.num_frames:
                diff = self.num_frames - len(frames)
                padding = torch.zeros(
                    (diff, *frames.shape[1:]),
                    dtype=frames.dtype
                )
                frames = torch.concatenate(
                    frames,
                    padding
                )

            entity_clips.append(frames)
            entity_masks.append(mask)
            logging.debug(
                "Video Clip: {}({}s~{}s), Completed!".format(
                    vid_path,
                    self.clip_duration * clip_of_video,
                    (self.clip_duration + 1) * clip_of_video
                )
            )

        del vid_reader

        entity_clips = torch.stack(entity_clips)
        entity_masks = torch.stack(entity_masks)

        entity_info = {
            "video_name": video_name,
            "df_type": df_type,
            "method": method,
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
        if self.pack:
            video_idx = idx
        else:
            video_idx = next(i for i, x in enumerate(self.stack_video_clips) if idx < x)
        return video_idx, *self.video_list[video_idx]

    def video_repr(self, idx):
        return '/'.join([str(i) for i in self.video_info(idx)[1:-1]])

    def video_meta(self, idx):
        df_type, method, name = self.video_info(idx)[1:4]
        meta_pool = self.video_table[df_type] if df_type == "REAL" else self.video_table["FAKE"][method]
        return meta_pool[name]


class TTDFDataModule(DeepFakeDataModule):
    def __init__(
        self,
        fake_methods=None,
        *args,
        **kargs
    ):
        super().__init__(*args, **kargs)
        self.fake_methods = fake_methods or TTDF.FAKE_METHODS

    def prepare_data(self):
        TTDF.prepare_data(self.data_dir, self.vid_ext, fake_methods=self.fake_methods)

    def setup(self, stage: str):
        data_cls = partial(
            TTDF,
            data_dir=self.data_dir,
            vid_ext=self.vid_ext,
            num_frames=self.num_frames,
            clip_duration=self.clip_duration,
            transform=self.transform,
            ratio=self.ratio,
            split="test" if stage in {"test", "predict"} else "val",
            pack=self.pack,
            max_clips=self.max_clips,
            fake_methods=self.fake_methods
        )

        if stage in {"fit", "valid", "train", "validate"}:
            self._val_dataset = data_cls()
        elif stage in {"test", "predict", None}:
            dataset = data_cls()
            self._test_dataset = dataset
            self._predict_dataset = dataset
