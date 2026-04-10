# Fix for Parser Error: "No action for key 'enable_ccsa'"

## Problem

When running the training command:
```bash
python main.py --config configs/base.yaml --config configs/clip/L14/ffg.yaml
```

You encountered this error:
```
error: Parser key "model":

  Problem with given class_path 'src.model.clip.svl.FFGSynoVideoLearner':

    Validation failed: No action for key "enable_ccsa" to check its value.
```

## Root Cause

The Lightning CLI argument parser was trying to validate the `enable_ccsa` parameter from the configuration file, but it couldn't find this parameter in the `FFGSynoVideoLearner.__init__()` method signature.

The issue was that:
1. `SynoVideoLearner` (parent class) has `enable_ccsa`, `ccsa_dropout`, and `ccsa_num_layers` parameters
2. `FFGSynoVideoLearner` (child class) inherits from `SynoVideoLearner` but didn't include these parameters in its `__init__` signature
3. The Lightning CLI uses introspection to validate configuration parameters against the class constructor signature

## Solution

Added the CCSA parameters to both `FFGSynoVideoLearner` and `FFESynoVideoLearner` class constructors:

### Changes Made

#### 1. Updated `FFGSynoVideoLearner.__init__()` signature:

```python
class FFGSynoVideoLearner(SynoVideoLearner):
    def __init__(
        self,
        # ... other parameters ...
        
        # CCSA parameters (ADDED)
        enable_ccsa: bool = True,
        ccsa_dropout: float = 0.5,
        ccsa_num_layers: int = -1,
    ):
```

#### 2. Updated `FFGSynoVideoLearner.super().__init__()` call:

```python
        super().__init__(
            # ... other parameters ...
            enable_ccsa=enable_ccsa,
            ccsa_dropout=ccsa_dropout,
            ccsa_num_layers=ccsa_num_layers
        )
```

#### 3. Applied the same fix to `FFESynoVideoLearner` class

## Verification

✅ Python syntax check passed:
```bash
python -m py_compile src/model/clip/svl.py
```

## What This Means

Now the Lightning CLI can properly:
1. Parse the `enable_ccsa`, `ccsa_dropout`, and `ccsa_num_layers` parameters from your YAML config
2. Validate that these parameters exist in the class constructor
3. Pass them correctly to the model initialization

## Your Configuration

Your current config (`configs/clip/L14/ffg.yaml`) should now work correctly:

```yaml
model:
  class_path: src.model.clip.svl.FFGSynoVideoLearner
  init_args:
    num_frames: 10
    architecture: ViT-L/14
    ksize_s: 5
    ksize_t: 5
    s_k_attr: 'k' 
    s_v_attr: 'emb' 
    t_attrs: ["q","k","v"]
    face_feature_path: "misc/L14_real_semantic_patches_v4_2000.pickle"
    face_parts: ["lips","skin","eyes","nose"]
    # CCSA configuration
    enable_ccsa: true
    ccsa_num_layers: 6  # Only use CCSA in last 6 layers (out of 24)
```

## Next Steps

You can now run your training command:

```bash
python main.py --config configs/base.yaml --config configs/clip/L14/ffg.yaml
```

The parser error should be resolved! 🎉

