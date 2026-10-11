# Cadenza experimental music model

A small autoregressive neural event predictor, combined with generated musical form and heuristic candidate selection. It creates MIDI note sequences; sampled recordings provide playback.

Architecture, training statistics, loss history and unconditional baselines are recorded in `dist/training-report.json`. The main model has 201,700 parameters and eight events of context. The title network and six dedicated instrument networks have separate reports. The model weights are JSON tensors for the bundled JS runtime, not a Transformers checkpoint.

Data: MAESTRO v3 official train/validation/test splits plus Mutopia supplements excluding composers present anywhere in MAESTRO. Specialist models use composer-disjoint splits and source MIDI program labels; labels were not verified by an orchestration expert. Provenance and archive hashes are retained.

Evaluation: general-model held-out losses beat unconditional frequency baselines across six heads. Specialist aggregate loss beats the baseline for each family; clarinet harmony quality does not individually beat its baseline. String validation and test contain only one composer each. No blinded listening evaluation or claim of artistic superiority has been made.

Limitations: short context, rule-driven larger form, limited rhythm/harmony vocabularies, approximate instrument metadata, stylistic bias toward the source corpora, imperfect title semantics and partial fragment matching. New sampled sequences can resemble existing music. More files or lower prediction loss do not prove greater musical quality.

Intended use: noncommercial experimentation, studying local generation and editable MIDI composition. See README and MODEL_LICENSE.md for code, data, model and sample licensing distinctions.
