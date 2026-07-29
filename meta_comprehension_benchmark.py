"""Barrière V0.10 pour les relations simples et la connaissance de soi."""

from __future__ import annotations

from kairos import Kernel


def main() -> int:
    kernel = Kernel()
    cas = []

    def verifier(nom: str, condition: bool) -> None:
        cas.append((nom, condition))

    self_answer = kernel.traiter("explique-toi")
    verifier("self_route", self_answer.route == "self.explain")
    verifier("self_target", self_answer.analyse.cible.valeur == "self:kairos")
    verifier("runtime_version", "0.12.0" in self_answer.reponse)

    relations = kernel.comprendre.analyser(
        "Kairos est un moteur symbolique"
    ).relations
    graphe = {(r.source, r.relation, r.target) for r in relations}
    verifier("proper_subject", ("self:kairos", "est_un", "moteur") in graphe)
    verifier("adjective_relation", ("moteur", "qualite", "symbolique") in graphe)

    action_graph = {
        (r.source, r.relation, r.target)
        for r in kernel.comprendre.analyser("Jps crée Kairos").relations
    }
    verifier(
        "proper_action",
        ("creator:jps", "creer", "self:kairos") in action_graph,
    )

    kernel.traiter("installe python")
    understood = kernel.traiter("qu'as-tu compris ?")
    verifier("understanding_route", understood.route == "understanding.explain")
    verifier("understanding_action", "installer" in understood.reponse)
    verifier("understanding_target", "python" in understood.reponse)

    kernel.traiter("analyse blorpe")
    unknown = kernel.traiter("qu'as-tu mal compris ?")
    verifier("unknown_route", unknown.route == "understanding.explain")
    verifier("unknown_word", "blorpe" in unknown.reponse)

    reussis = sum(ok for _, ok in cas)
    total = len(cas)
    print(f"META_COMPREHENSION_BENCHMARK: {reussis}/{total}")
    for nom, ok in cas:
        print(f"[{'PASS' if ok else 'FAIL'}] {nom}")
    return 0 if reussis == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
