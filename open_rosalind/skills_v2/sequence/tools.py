"""Sequence analysis tools (local computation)."""
from Bio.Seq import Seq
from Bio.SeqUtils import molecular_weight, gc_fraction


def analyze(sequence: str) -> dict:
    """Analyze DNA/RNA/protein sequence (local computation)."""
    sequence = sequence.strip()

    # Handle both FASTA and raw sequences
    if sequence.startswith('>'):
        blocks = sequence.split('>')[1:]
    else:
        blocks = [f"seq\n{sequence}"]

    records = []
    for block in blocks:
        lines = block.strip().split('\n')
        header = lines[0] if lines else 'seq'
        seq_str = ''.join(lines[1:] if len(lines) > 1 else [lines[0]]).replace(' ', '').replace('\n', '').upper()

        if not seq_str:
            continue

        seq_obj = Seq(seq_str)
        seq_type = _detect_type(seq_str)

        rec = {
            'header': header,
            'sequence': seq_str,
            'length': len(seq_str),
            'type': seq_type,
            'composition': {base: seq_str.count(base) for base in set(seq_str)},
        }

        if seq_type == 'dna':
            rec['gc_content'] = round(gc_fraction(seq_obj) * 100, 2)
            try:
                rec['translation'] = str(seq_obj.translate(to_stop=False))
            except:
                rec['translation'] = None
            rec['reverse_complement'] = str(seq_obj.reverse_complement())
        elif seq_type == 'protein':
            try:
                rec['molecular_weight'] = round(molecular_weight(seq_obj, 'protein') / 1000, 2)
            except:
                rec['molecular_weight'] = None

        records.append(rec)

    return {'records': records, 'n_records': len(records)}


def _detect_type(seq: str) -> str:
    """Detect sequence type (dna, rna, protein)."""
    seq_upper = seq.upper()
    dna_bases = set('ATCGN')
    rna_bases = set('AUCGN')

    if set(seq_upper) <= dna_bases:
        return 'dna'
    elif set(seq_upper) <= rna_bases:
        return 'rna'
    else:
        return 'protein'
