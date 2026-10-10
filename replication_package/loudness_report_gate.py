#!/usr/bin/env python3
"""fresh N1 derived-report generation and strict gate.

Standard library only. Reuses the reviewed loudness_analysis module; it neither
imports the scorer nor runs scientific cases. All paths are explicit at the gate
interface. CLI default validates references without writing any output.
"""
import argparse
import importlib.util
import json
from pathlib import Path

EXPECTED_FILES = frozenset(('loudness-analysis.json', 'loudness-sensitivity.tex',
                            'summary.json', 'output-sha256.json'))


class GateError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise GateError(message)


def load_analyzer(path):
    path = Path(path).resolve()
    spec = importlib.util.spec_from_file_location('reviewed_loudness_analysis', path)
    require(spec is not None and spec.loader is not None, 'cannot load reviewed analyzer')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_references(*, source_dir, analyzer_path, reference_json, reference_tex):
    """Read-only preflight. Both references must match pinned original records.

    This does not count as successful fresh generation. A caller must use
    regenerate_and_verify for the production reproduction summary.
    """
    a = load_analyzer(analyzer_path)
    source = a.load_source(Path(source_dir))
    reference = a.read_json(Path(reference_json))
    a.validate_report(reference, source)
    require(Path(reference_tex).read_bytes() == a.tex_table(reference).encode(),
            'reference TeX differs from complete source-derived report')
    return a, source, reference


def _write_generated(a, source, out):
    """Actual bounded generation, deliberately separate for missing-write tests.

    Never copy a reference report. Build all three files afresh from validated
    original records; the existing analyzer owns all counting and rendering.
    """
    report = a.build_report(source)
    outputs = {'loudness-analysis.json': a.encoded(report),
               'loudness-sensitivity.tex': a.tex_table(report).encode(),
               'summary.json': a.encoded(a.summary(report))}
    for name, data in outputs.items():
        with (out/name).open('xb') as stream:
            stream.write(data)
    manifest = {name: a.digest(data) for name, data in outputs.items()}
    with (out/'output-sha256.json').open('xb') as stream:
        stream.write(a.encoded(manifest))


def regenerate_and_verify(*, source_dir, analyzer_path, reference_json, reference_tex, out_dir):
    """Create a new private output directory, generate, and validate everything.

    out_dir must not exist. The source/reference directories are never output
    destinations. Partial output remains inspectable on failure, but no success
    summary is returned. A subsequent attempt must choose another fresh path.
    """
    source_path=Path(source_dir).resolve()
    out=Path(out_dir).resolve()
    refs=[Path(reference_json).resolve(),Path(reference_tex).resolve()]
    require(not out.exists(), 'output directory already exists; inherited output is not fresh generation')
    require(out != source_path and source_path not in out.parents and out not in source_path.parents,
            'output must be outside source tree and cannot contain it')
    require(all(out != r.parent and out not in r.parents for r in refs), 'output cannot contain or replace references')
    a, source, reference=validate_references(source_dir=source_path, analyzer_path=analyzer_path,
                                           reference_json=refs[0], reference_tex=refs[1])
    # Atomic exclusive directory creation is the freshness boundary. No inherited
    # report is present here, even when it is byte-for-byte valid historical data.
    out.mkdir(parents=True, exist_ok=False)
    _write_generated(a, source, out)
    require({p.name for p in out.iterdir()} == EXPECTED_FILES, 'fresh generator omitted a required file or wrote unexpected files')
    require(all((out/n).is_file() and not (out/n).is_symlink() for n in EXPECTED_FILES),
            'fresh outputs must be regular files, not inherited symlinks')
    actual=a.read_json(out/'loudness-analysis.json')
    # Independently reload disk inputs and verify all 252 pins after generation;
    # source-derived comparison includes all 93 original per-method predictions.
    after=a.load_source(source_path)
    require(a.strict_equal(source, after), 'pinned source changed during generation')
    a.validate_report(actual, after)
    require(a.strict_equal(actual, reference), 'fresh full JSON differs from source-validated reference')
    require((out/'loudness-sensitivity.tex').read_bytes() == a.tex_table(actual).encode(),
            'fresh TeX differs from full JSON')
    require((out/'loudness-sensitivity.tex').read_bytes() == refs[1].read_bytes(),
            'fresh TeX differs from source-validated reference TeX')
    require(a.strict_equal(a.read_json(out/'summary.json'), a.summary(actual)), 'summary schema/types/values differ')
    expected_hashes={n:a.digest((out/n).read_bytes()) for n in sorted(EXPECTED_FILES-{'output-sha256.json'})}
    require(a.strict_equal(a.read_json(out/'output-sha256.json'),expected_hashes), 'fresh output hash manifest differs')
    return {'status':'verified_derived_report', 'implementation_status':'INSTALLED_DERIVED_ANALYSIS',
            'fresh_generation_verified':True,'source_pin_count':len(after['input_sha256']),
            'original_failure_prediction_count':len(actual['original_failure_predictions']),
            'original_predictions_sha256':actual['original_predictions_sha256'],
            'complete_json_and_scalar_types_verified':True,'tex_matches_json_and_reference':True,
            'all_scenarios_corpora_methods_verified':True,'outputs_sha256':expected_hashes}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source',type=Path,required=True)
    ap.add_argument('--analyzer',type=Path,required=True)
    ap.add_argument('--reference-json',type=Path,required=True)
    ap.add_argument('--reference-tex',type=Path,required=True)
    ap.add_argument('--write',action='store_true')
    ap.add_argument('--out',type=Path)
    args=ap.parse_args()
    kwargs={'source_dir':args.source,'analyzer_path':args.analyzer,
            'reference_json':args.reference_json,'reference_tex':args.reference_tex}
    try:
        require(args.write == (args.out is not None),'--write and --out must be supplied together')
        if args.write:
            result=regenerate_and_verify(**kwargs,out_dir=args.out)
        else:
            validate_references(**kwargs)
            result={'status':'references_validated_only','fresh_generation_verified':False,'wrote_outputs':False,
                    'implementation_status':'INSTALLED_DERIVED_ANALYSIS'}
        print(json.dumps(result,sort_keys=True,indent=2))
        return 0
    except (OSError,ValueError,KeyError,TypeError) as e:
        print('INVALID: '+str(e))
        return 2


if __name__=='__main__':
    raise SystemExit(main())
