import unittest

from web_app.biology_tools import fasta_records, protein_sequence_validation_error


class ProteinSequenceParsingTests(unittest.TestCase):
    def test_invalid_sequence_preserves_problem_characters(self) -> None:
        records = fasta_records(">bad_sequence\nATGCXYZ123")
        self.assertEqual(len(records), 1)
        error = protein_sequence_validation_error(records[0]["raw_sequence"])
        self.assertIn("X、Y、Z、1、2、3", error)
        self.assertIn("本次未执行 BLAST", error)

    def test_instruction_after_fasta_is_not_parsed_as_sequence(self) -> None:
        text = (
            ">test_protein\n"
            "MKWVTFISLLFLFSSAYSRGVFRRDTHKSEIAHRFKDLGE\n"
            "请检查序列类型、长度，并给出下一步分析建议。"
        )
        records = fasta_records(text)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["sequence"], "MKWVTFISLLFLFSSAYSRGVFRRDTHKSEIAHRFKDLGE")
        self.assertEqual(protein_sequence_validation_error(records[0]["raw_sequence"]), "")

    def test_english_instruction_after_fasta_is_not_parsed_as_sequence(self) -> None:
        text = ">test_protein\nMKWVTFISLLFLFSSAYSRGVFRRDTHKSEIAHRFKDLGE\nPlease check sequence type and length."
        records = fasta_records(text)
        self.assertEqual(records[0]["sequence"], "MKWVTFISLLFLFSSAYSRGVFRRDTHKSEIAHRFKDLGE")


if __name__ == "__main__":
    unittest.main()
