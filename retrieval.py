import math
import re
from collections import Counter

from query_parser import normalize

TOKEN_RE = re.compile(r"\w+", re.UNICODE)


def features(text):
    feats = Counter()
    for tok in TOKEN_RE.findall(normalize(text)):
        if len(tok) < 2:
            continue
        feats["w:" + tok] += 1
        if len(tok) >= 3:
            padded = f"#{tok}#"
            for i in range(len(padded) - 2):
                feats["c:" + padded[i:i + 3]] += 1
    return feats


class POIIndex:

    def __init__(self, pois):
        self.pois = pois
        self.n = len(pois)
        docs = [features(p.get("search_text") or p.get("name", "")) for p in pois]
        df = Counter()
        for d in docs:
            df.update(d.keys())
        self.idf = {f: math.log((self.n + 1) / (c + 1)) + 1 for f, c in df.items()}
        self.default_idf = math.log(self.n + 1) + 1
        self.vecs = [self._vec(d) for d in docs]

    def _vec(self, feats):
        v = {f: (1 + math.log(c)) * self.idf.get(f, self.default_idf) for f, c in feats.items()}
        norm = math.sqrt(sum(x * x for x in v.values())) or 1.0
        return {f: x / norm for f, x in v.items()}

    def scores(self, query_text, indices):
        qv = self._vec(features(query_text))
        out = {}
        for i in indices:
            dv = self.vecs[i]
            small, big = (qv, dv) if len(qv) < len(dv) else (dv, qv)
            out[i] = sum(x * big.get(f, 0.0) for f, x in small.items())
        return out