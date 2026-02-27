from __future__ import annotations

from dataclasses import dataclass
import re

from django.db.models import Q

from articles.models import Article


@dataclass
class _Collectible:
    tag_code: str
    display_label: str


def recommended_articles(_conditions: list) -> list[dict]:
    condition_names: list[str] = []
    for row in _conditions or []:
        if isinstance(row, dict):
            name = (row.get("name") or "").strip()
        else:
            name = str(row).strip()
        if name:
            condition_names.append(name)

    queryset = Article.objects.filter(status="approved").order_by("-created_at")
    if not condition_names:
        return []

    matched: list[dict] = []
    seen_ids: set[int] = set()
    for condition in condition_names:
        condition_words = [w for w in re.split(r"[^a-zA-Z0-9]+", condition) if len(w) > 2]
        if not condition_words:
            continue
        token_query = Q()
        for token in condition_words[:4]:
            token_query |= Q(title__icontains=token) | Q(content__icontains=token)
        scoped = queryset.filter(token_query)
        for article in scoped[:3]:
            if article.id in seen_ids:
                continue
            seen_ids.add(article.id)
            snippet = (article.content or "").strip().replace("\n", " ")
            if len(snippet) > 180:
                snippet = snippet[:180].rstrip() + "..."
            matched.append(
                {
                    "title": article.title,
                    "summary": snippet,
                    "url": f"/articles/?q={article.title}",
                    "category": article.category,
                }
            )
            if len(matched) >= 6:
                return matched
    return matched


def issue_collectible_tag(_session=None, _condition=None):
    return _Collectible(tag_code="HS-AI-TRIAGE", display_label="Health Insight Pass")
