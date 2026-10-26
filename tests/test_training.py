"""python3 -m unittest — the model trains with nothing installed (termnl/model.py, 26 Oct 2026)."""
import sys
import unittest

from termnl.model import classify, train_classifier

EXAMPLES = [{"text": t, "label": l} for l, ts in {
    "open": ["open the file", "open my notes", "show me the file", "open it", "display the file", "open notes"],
    "delete": ["delete the file", "remove my notes", "erase the file", "delete it", "get rid of the file", "remove notes"],
    "none": ["what a nice day", "tell me a joke", "I like tea", "the weather is nice", "a joke please", "nice tea"],
}.items() for t in ts]


class Training(unittest.TestCase):
    def test_it_trains_without_numpy(self):
        kept = sys.modules.get("numpy")
        sys.modules["numpy"] = None  # import numpy now fails
        try:
            model = train_classifier(EXAMPLES, passes=4, settle=10)
        finally:
            if kept is None:
                del sys.modules["numpy"]
            else:
                sys.modules["numpy"] = kept
        self.assertEqual(model["labels"], ["delete", "none", "open"])
        self.assertEqual(classify(model, "please open the notes")[0]["label"], "open")
        self.assertEqual(classify(model, "remove the file")[0]["label"], "delete")
        self.assertTrue(all(-127 <= w <= 127 for row in model["weights"].values() for w in row[1:]))

    def test_the_same_sentences_give_the_same_model(self):
        self.assertEqual(train_classifier(EXAMPLES, passes=4, settle=10), train_classifier(EXAMPLES, passes=4, settle=10))
