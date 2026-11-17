import re
from pathlib import Path
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline


class Categorizer:
    def __init__(
        self,
        model_path: str = "models/categorizer_model.pkl",
        rules_path: str = "rules/default_rules.yaml",
    ):
        self.model_path = Path(model_path)
        self.rules_path = Path(rules_path)
        self.pipeline: Pipeline | None = (
            joblib.load(self.model_path) if self.model_path.exists() else None
        )
        self.rules: dict[str, str] = self._load_rules()

    def _load_rules(self) -> dict[str, str]:
        try:
            with open(self.rules_path, "r", encoding="utf-8") as f:
                return self._parse_yaml(f.read())
        except FileNotFoundError:
            return {}

    def _parse_yaml(self, content: str) -> dict[str, str]:
        import yaml
        return yaml.safe_load(content) or {}

    def categorize(self, descriptions: list[str] | str) -> list[tuple[str, float]]:
        if isinstance(descriptions, str):
            descriptions = [descriptions]

        results: list[tuple[str, float]] = []
        for desc in descriptions:
            matched_category = None
            for pattern, category in self.rules.items():
                if re.search(pattern, desc, re.IGNORECASE):
                    matched_category = category
                    break

            if matched_category:
                results.append((matched_category, 1.0))
            elif self.pipeline is not None:
                pred = str(self.pipeline.predict([desc])[0])
                proba = float(self.pipeline.predict_proba([desc])[0].max())
                results.append((pred, proba))
            else:
                results.append(("Não Categorizado", 0.0))

        return results

    def train(self, data: list[str], labels: list[str]) -> None:
        self.pipeline = Pipeline([
            ("vectorizer", TfidfVectorizer(ngram_range=(1, 2))),
            ("classifier", LogisticRegression(class_weight="balanced", max_iter=1000)),
        ])
        self.pipeline.fit(data, labels)
        self.model_path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.pipeline, self.model_path)
