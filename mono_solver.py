"""
Quebra de cifras de substituição monoalfabética sem espaços.

Estratégia: o texto claro é uma concatenação de palavras do dicionário.
Fazemos uma busca em profundidade (DFS) que, a partir da posição atual do
criptograma, tenta encaixar cada palavra do dicionário cujo *padrão* de
letras repetidas coincide com o trecho cifrado e que seja consistente com o
mapeamento cifra->claro construído até ali (o mapeamento precisa ser
injetivo nos dois sentidos). Quando o criptograma inteiro é coberto, temos
uma solução. Entre as soluções encontradas escolhemos a com menos palavras.
"""

import re
import sys
import time
from collections import defaultdict

BASE = __import__("os").path.dirname(__file__)
VIGENERE = {7, 11, 17, 22, 27, 33, 37, 44, 47, 55, 57, 66, 67}


def load_cryptograms(path):
    text = open(path).read()
    return {int(n): c for n, c in re.findall(r"#(\d+), tamanho: \d+\n([A-Z]+)", text)}


def load_words(path):
    return sorted({w.strip() for w in open(path) if w.strip()}, key=len, reverse=True)


def pattern(s):
    seen = {}
    return tuple(seen.setdefault(ch, len(seen)) for ch in s)


def score(words):
    """Menor é melhor: lacuna mínima e, depois, palavras mais longas
    (soma dos quadrados dos tamanhos), que são muito menos prováveis de
    encaixar por acaso do que sequências de palavras curtas. Cada palavra
    custa 1 ponto para desempatar a favor de menos palavras."""
    gap = sum(len(w) - 2 for w in words if w.startswith("["))  # letras sem palavra (sem os colchetes)
    real = [w for w in words if not w.startswith("[")]
    return (gap, -sum(len(w) ** 2 for w in real) + len(real))


def solve(cipher, words, max_solutions=2000, time_limit=20.0, max_gap=0):
    """Busca por cobertura do criptograma com palavras do dicionário.

    max_gap > 0 permite (uma única vez) um trecho de até max_gap letras que
    não corresponde a nenhuma palavra do dicionário — usado quando o texto
    claro contém uma palavra ausente da lista.
    """
    by_len = defaultdict(list)
    for w in words:
        by_len[len(w)].append((w, pattern(w)))
    lengths = sorted(by_len, reverse=True)
    n = len(cipher)
    # pré-computa os padrões de cada trecho do criptograma
    pat_cache = {}

    def sub_pattern(i, L):
        key = (i, L)
        if key not in pat_cache:
            pat_cache[key] = pattern(cipher[i:i + L])
        return pat_cache[key]

    solutions = []
    fwd, rev = {}, {}
    path = []
    dead = set()  # (posição, mapeamento congelado) sem saída — memo de falhas
    deadline = time.time() + time_limit

    def dfs(i, gap_left=max_gap):
        if time.time() > deadline or len(solutions) >= max_solutions:
            return True
        if i == n:
            solutions.append((list(path), dict(fwd)))
            return True
        key = (i, gap_left, frozenset(fwd.items()))
        if key in dead:
            return False
        found = False
        # trecho desconhecido: as letras ficam sem mapeamento (exibidas como '?')
        for L in range(1, min(gap_left, n - i) + 1):
            path.append("[" + cipher[i:i + L] + "]")
            if dfs(i + L, 0):
                found = True
            path.pop()
        for L in lengths:
            if i + L > n:
                continue
            sp = sub_pattern(i, L)
            seg = cipher[i:i + L]
            for w, wp in by_len[L]:
                if wp != sp:
                    continue
                added = []
                ok = True
                for c, p in zip(seg, w):
                    if c in fwd:
                        if fwd[c] != p:
                            ok = False
                            break
                    elif p in rev:
                        ok = False
                        break
                    else:
                        fwd[c] = p
                        rev[p] = c
                        added.append(c)
                if ok:
                    path.append(w)
                    if dfs(i + L, gap_left):
                        found = True
                    path.pop()
                for c in added:
                    del rev[fwd.pop(c)]
                if len(solutions) >= max_solutions or time.time() > deadline:
                    return True
        if not found:
            dead.add(key)
        return found

    dfs(0)
    solutions.sort(key=lambda s: score(s[0]))
    return solutions


def decrypt(cipher, mapping):
    return "".join(mapping.get(ch, "?") for ch in cipher)


def main():
    crypt = load_cryptograms(f"{BASE}/docs/criptogramas2.txt")
    words = load_words(f"{BASE}/docs/dicionario2.txt")
    ids = [int(a) for a in sys.argv[1:]] or [k for k in sorted(crypt) if k not in VIGENERE]

    for k in ids:
        c = crypt[k]
        sols = solve(c, words)
        if not sols:  # alguma palavra não está no dicionário: permite uma lacuna
            sols = solve(c, words, max_gap=12)
        if not sols:
            print(f"#{k:2d} ({len(c)}) SEM SOLUÇÃO\n     cifra : {c}")
            continue
        best_words, mapping = sols[0]
        key = "".join(mapping.get(ch, ".") for ch in "ABCDEFGHIJKLMNOPQRSTUVWXYZ")
        alts = [" ".join(s[0]) for s in sols[1:4]]
        print(f"#{k:2d} ({len(c)}) {' '.join(best_words)}")
        print(f"     cifra : {c}\n     claro : {decrypt(c, mapping)}"
              f"\n     chave : ABCDEFGHIJKLMNOPQRSTUVWXYZ -> {key}"
              f"\n     [{len(sols)} segmentações válidas]"
              + "".join(f"\n     alt   : {a}" for a in alts))


if __name__ == "__main__":
    main()
