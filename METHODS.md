# Recorded model-based annotation method

The specifications, interface descriptions and adjudication records are model-generated research inputs. They are not independent human reference labels. Replaying the frozen numerical analysis does not recreate the models, validate their judgments or establish prospective detector performance.

## Adjudication roles

| Public role | Recorded model and use |
| --- | --- |
| ADJ1 (`adj1`) | gpt-6-astra; recorded command-line client version 0.149.0. Pilot A1/A2 used medium reasoning effort; the later frozen launcher requested high effort. |
| ADJ2 (`adj2`) | GLM-5.2 through provider identifier `zai/glm-5.2`, requesting high thinking. |
| ADJ3 (`adj3`) | DeepSeek V4 Pro through provider identifier `deepseek/deepseek-v4-pro`, requesting high thinking. |
| `withdrawn_google` | Gemini-3.1-pro-high. The corpus A1 records were withdrawn on 2026-09-27 after calibration yielded 6/16; these remain withdrawn evidence. |
| `calibration_kimi` | Kimi K3 calibration candidate; its recorded calibration scores are retained. It was not selected for an active ADJ1, ADJ2 or ADJ3 seat. |
| `adj1_repeat` | A second gpt-6-astra run, not used as a deciding independent model because a repeated ADJ1 model would decide every split. |

These identifiers describe the historical study, not the newest models available today. The stage-specific protocol, prompts, ledgers, per-item decisions, disagreements and withdrawal reasons remain the scientific record; this table is not a substitute for them. S1/S2 model specifications remain in the protocol and freeze metadata.

## Historical execution settings

The initial ADJ1 launcher requested high reasoning effort, a writable task workspace and network access. Port-provenance ADJ1 launch commands requested high effort and a writable workspace; they did not explicitly enable network access. This difference is retained rather than treating all launches as identically isolated.

The withdrawn Google launch used a 40-minute process timeout. The GLM/DeepSeek launchers requested high thinking and a 3,600-second timeout with a fresh execution session. Their generated prompts received an additional operational line directing outputs to the task workspace with absolute paths; this was a workspace instruction, not a scientific judging criterion. The public edition omits machine-specific shell launching and queue scripts. Packet preparation, collection and the recorded scientific prompts remain inspectable.

The two-seat port batch launcher ran two packets at a time across ADJ1 and ADJ2 (four processes). A separate queue used two concurrent packets by default; a documented ADJ3 example used four. These are recorded scheduling settings, not proof of stochastic independence. Omitted wrappers also contained local proxy/keychain/background-process handling; none is required by the offline numerical reproduction command.

The original execution-client names and machine paths are retained in the author's private archive. Neutral public role identifiers do not change the model family, the status of withdrawn runs, any recorded judgment, or the voting/folding rules.
