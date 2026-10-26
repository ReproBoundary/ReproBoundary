# Trajectory redaction policy

Released logs are generated mechanically from the frozen archive. The exporter replaces local home and shared-storage paths, authorization and cookie headers, recognized API/service keys, credential assignments, JWTs, secret query parameters, and private-key blocks. It does not rewrite scientific statements or tool outputs except where those patterns occur. Every run records the number of substitutions and both source and released log hashes.

The release intentionally omits raw security telemetry and API-usage payloads. Before public upload, run the verifier and perform an independent spot review of high-redaction logs. A zero redaction count means no configured pattern matched; it is not a general proof that a log contains no sensitive information.
