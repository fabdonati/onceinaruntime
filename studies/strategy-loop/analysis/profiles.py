"""Position activity from completed-close EMA targets, outside benchmark timing."""
import argparse
import csv
from itertools import combinations
import json
from pathlib import Path
import statistics

from historical import digest
from reference import features


def activity(targets, first, block_size=256):
    """Opening state at t uses target[t-1]; terminal liquidation is excluded."""
    previous, length, changes, held = False, 0, 0, 0
    completed, blocks = [], []
    for offset,t in enumerate(range(first,len(targets))):
        if offset % block_size == 0:
            blocks.append(dict(start_bar=t,bars=0,changes=0))
        current = bool(targets[t-1])
        transition = current != previous
        changes += transition
        blocks[-1]['changes'] += transition
        blocks[-1]['bars'] += 1
        held += current
        if current:
            length += 1
        elif previous:
            completed.append(length); length = 0
        previous = current
    return dict(changes=changes,held_bars=held,eligible_bars=max(0,len(targets)-first),
                completed=completed,censored=[length] if previous else [],blocks=blocks)


def quartiles(values):
    if not values:
        return dict(q1=None,median=None,q3=None)
    if len(values) == 1:
        return dict(q1=values[0],median=values[0],q3=values[0])
    q1,median,q3 = statistics.quantiles(values,n=4,method='inclusive')
    return dict(q1=q1,median=median,q3=q3)


def describe(bars, spans, counts=(64,1128)):
    matrix = features(bars,spans)
    per_config, raw = [], []
    for index,(f,s) in enumerate(combinations(range(len(spans)),2)):
        if index >= max(counts): break
        a = activity([row[f] > row[s] for row in matrix],max(spans))
        raw.append(a)
        per_config.append(dict(config=index,fast=spans[f],slow=spans[s],
            changes=a['changes'],held_bars=a['held_bars'],eligible_bars=a['eligible_bars'],
            completed_spells=len(a['completed']),holding_bars=quartiles(a['completed']),
            censored_lengths=a['censored']))
    aggregates=[]
    for k in counts:
        rows=raw[:k]; updates=sum(a['eligible_bars'] for a in rows)
        completed=[v for a in rows for v in a['completed']]
        blocks=[]
        for i,b in enumerate(rows[0]['blocks']):
            changes=sum(a['blocks'][i]['changes'] for a in rows)
            blocks.append(dict(start_bar=b['start_bar'],bars=b['bars'],changes=changes,
                               changes_per_1000=1000*changes/(k*b['bars'])))
        aggregates.append(dict(configs=k,strategy_bars=updates,
            changes=sum(a['changes'] for a in rows),
            changes_per_1000=1000*sum(a['changes'] for a in rows)/updates,
            long_fraction=sum(a['held_bars'] for a in rows)/updates,
            completed_spells=len(completed),holding_bars=quartiles(completed),
            censored_spells=sum(bool(a['censored']) for a in rows),
            censored_lengths=[v for a in rows for v in a['censored']],blocks=blocks))
    return dict(configurations=per_config,aggregates=aggregates)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--datasets',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    manifest=json.loads(args.datasets.read_text())
    args.output.mkdir(parents=True,exist_ok=False)
    output=dict(input_manifest_sha256=digest(args.datasets),spans=list(range(2,97,2)),
                definitions=__doc__,datasets=[])
    for item in manifest['datasets']:
        path=args.datasets.parent/item['file']
        if digest(path)!=item['file_sha256']: raise ValueError('input hash differs')
        with path.open() as file:
            bars=[(int(r['timestamp']),float(r['open']),float(r['close'])) for r in csv.DictReader(file)]
        result=describe(bars,output['spans'])
        name=item['dataset_id']+'.json'
        (args.output/name).write_text(json.dumps(result,indent=2)+'\n')
        output['datasets'].append(dict(item,file=name,file_sha256=digest(args.output/name)))
        print(item['dataset_id'],flush=True)
    (args.output/'manifest.json').write_text(json.dumps(output,indent=2)+'\n')


if __name__=='__main__': main()
