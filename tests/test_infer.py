from resourcepacks import engine, infer, review


def test_confident_decisions_are_right_and_the_rest_go_to_the_admin(world, cfg):
    confident = wrong = 0
    for c in world.customers:
        d = infer.draft(world.workspace(c.id), cfg, world.today)
        for it in d["items"]:
            if it["kind"] == "rule" or it["confidence"] < cfg["review_threshold"]:
                continue
            confident += 1
            wrong += world.admin_answer(c.id, it) != it["value"]
    assert confident > 300 and wrong == 0


def test_a_signed_off_pack_answers_like_the_truth(world, cfg):
    for c in world.customers:
        ws = world.workspace(c.id)
        d = infer.draft(ws, cfg, world.today)
        rv, _ = review.apply_admin(d, cfg["review_threshold"], lambda it, cid=c.id: world.admin_answer(cid, it))
        full = review.apply_workshop(rv, world.workshop(c.id))
        truth = world.truth_pack(c.id)
        for q in world.questions(c.id):
            assert engine.same(
                engine.answer(ws, full, q["query"], world.today), engine.answer(ws, truth, q["query"], world.today)
            ), (c.id, q)


def test_unknown_status_words_are_guessed_and_queued_not_trusted(cfg):
    from datetime import date

    ws = {
        "customer": "X",
        "sheets": [
            {
                "id": 1,
                "name": "Plan",
                "columns": [
                    {"id": 10, "title": "Item", "type": "TEXT_NUMBER", "primary": True},
                    {"id": 11, "title": "Météo", "type": "PICKLIST", "options": ["Rouge", "Orange", "Vert"]},
                    {"id": 12, "title": "Début", "type": "DATE"},
                    {"id": 13, "title": "Échéance", "type": "DATE"},
                ],
                "rows": [
                    {
                        "id": i,
                        "parentId": None,
                        "cells": [
                            {"columnId": 10, "value": f"t{i}"},
                            {"columnId": 11, "value": "Vert"},
                            {"columnId": 12, "value": "2026-10-01"},
                            {"columnId": 13, "value": f"2026-10-{10 + i:02d}"},
                        ],
                    }
                    for i in range(12)
                ],
            }
        ],
    }
    d = infer.draft(ws, cfg, date(2026, 11, 16))
    t = next(iter(d["templates"].values()))
    assert t["roles"]["start"] == "Début" and t["roles"]["due"] == "Échéance"
    queued = {i["key"] for i in review.queue(d, cfg["review_threshold"])}
    assert {"Rouge", "Orange", "Vert"} <= queued and "Météo" in queued


def test_a_sheet_named_as_an_archive_is_left_out(world, cfg):
    c = next(c for c in world.customers if c.archive_style == "prefix")
    d = infer.draft(world.workspace(c.id), cfg, world.today)
    for s in c.sheets:
        if s["name"].startswith("ARCHIVE"):
            assert d["sheets"][str(s["id"])]["kind"] == "archive"
