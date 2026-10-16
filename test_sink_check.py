# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
import unittest
import xml.etree.ElementTree as ET

import sink_check as sc


class Rules(unittest.TestCase):
    def test_on_topic(self):
        self.assertTrue(sc.on_topic("Orexin neurons and NEAT in mice"))
        self.assertTrue(sc.on_topic("Diet-induced obesity"))
        self.assertTrue(sc.on_topic("High-fat diet"))
        self.assertTrue(sc.on_topic("hepatic metabolism"))  # broad on purpose (works against H1)
        self.assertFalse(sc.on_topic("Skin microbiome of infected pressure ulcers"))
        # "neat" in lower case is an ordinary word, not NEAT
        self.assertFalse(sc.on_topic("a neat trick for CT artefacts"))
        self.assertFalse(sc.on_topic(None))

    def test_abstract_text(self):
        inv = {"Orexin": [0], "raises": [1], "activity": [2], "again": [4], "NEAT": [3]}
        self.assertEqual(sc.abstract_text(inv), "Orexin raises activity NEAT again")
        self.assertEqual(sc.abstract_text(None), "")

    def test_strip_doi_and_pmcid(self):
        self.assertEqual(sc.strip_doi("https://doi.org/10.1016/J.PHYSBEH.2017.03.040"), "10.1016/j.physbeh.2017.03.040")
        self.assertEqual(sc.strip_doi(None), "")
        self.assertEqual(sc.pmcid_of({"pmcid": "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5510739"}), "5510739")
        self.assertEqual(sc.pmcid_of({}), "")

    def test_wilson(self):
        # 24/25 by hand: p 0.96; centre (0.96 + 0.07683)/1.15366 = 0.89870;
        # half = 1.96*sqrt(0.0384/25 + 3.8416/2500)/1.15366 = 1.96*0.055426/1.15366 = 0.09417
        p, lo, hi = sc.wilson(24, 25)
        self.assertAlmostEqual(p, 0.96, places=6)
        self.assertAlmostEqual(lo, 0.8045, places=3)
        self.assertAlmostEqual(hi, 0.9929, places=3)

    def test_share_off(self):
        rows = [{"on_topic": False}] * 3 + [{"on_topic": True}]
        s = sc.share_off(rows)
        self.assertEqual((s["n"], s["off_topic"]), (4, 3))
        self.assertAlmostEqual(s["share"], 0.75)


class Refs(unittest.TestCase):
    def test_find_by_doi(self):
        refs = [{"key": "a", "DOI": "10.1/x"}, {"key": "b", "DOI": "10.1016/J.physbeh.2017.03.040"}]
        self.assertEqual(sc.find_target_ref(refs)["key"], "b")

    def test_find_by_text_garbled(self):
        refs = [{"key": "2348_CR121", "DOI": "10.1016/j.chempr.2016.07.007.Immunomodulatory",
                 "unstructured": "Kuschner O'connor, Butz AM (2017) HHS Public Access. Physiol Behav 176:139-148."}]
        hit = sc.find_target_ref(refs)
        d = sc.describe_ref(hit)
        self.assertTrue(d["hhs_banner"])
        self.assertFalse(d["doi_is_target"])
        self.assertFalse(d["real_title"])

    def test_not_found(self):
        self.assertIsNone(sc.find_target_ref([{"key": "a", "unstructured": "Smith 2001 Physiol Behav 70:1-9"}]))
        self.assertIsNone(sc.find_target_ref(None))


JATS = """<article><body>
<p>Wound healing is slow in older adults <xref ref-type="bibr" rid="CR5">5</xref>. Sedentary time was
not recorded <xref ref-type="bibr" rid="CR6 CR7">6,7</xref>. Next topic.</p>
<p>Unrelated paragraph <xref ref-type="bibr" rid="CR8">8</xref>.</p>
</body><back><ref-list>
<ref id="CR6"><mixed-citation>Bunney PE. Orexin activation counteracts decreases in nonexercise activity thermogenesis (NEAT).
<pub-id pub-id-type="doi">10.1016/j.physbeh.2017.03.040</pub-id></mixed-citation></ref>
</ref-list></back></article>"""


class Pmc(unittest.TestCase):
    def test_rid_and_context(self):
        root = ET.fromstring(JATS)
        rid, text = sc.target_rid(root)
        self.assertEqual(rid, "CR6")
        self.assertIn("nonexercise", text)
        ctx = sc.contexts(root, rid)
        self.assertEqual(len(ctx), 1)
        self.assertTrue(ctx[0].startswith("Sedentary time was not recorded [[*]]6,7"))
        self.assertTrue(sc.on_topic(ctx[0].replace("[[*]]", "")))

    def test_no_body(self):
        root = ET.fromstring("<article><back/></article>")
        self.assertEqual(sc.contexts(root, "CR1"), [])
        self.assertEqual(sc.target_rid(root), (None, ""))


if __name__ == "__main__":
    unittest.main()
