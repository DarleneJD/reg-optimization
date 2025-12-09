import py_dss_interface
import pandas as pd
import numpy as np
import os
import random
from scipy.special import gamma
import matplotlib.pyplot as plt

# ============================================================
# CONFIGURAÇÃO DO ARQUIVO
# ============================================================

dss_file = r"D:\Users\EdioD\PycharmProjects\variacao-tensao-frp\13Bus\23742222\IEEE13_v1.dss"
output_dir = os.path.dirname(dss_file)
eventlog_temp = os.path.join(output_dir, "FPA_EventLog.csv")

dss = py_dss_interface.DSS()

# Compila uma vez para descobrir quantos PVs existem
dss.text(f"compile [{dss_file}]")
dss.text("set voltagebases=[115, 4.16, 0.48]")
dss.text("calcvoltagebases")

num_pvs = dss.pvsystems.count
print(f"Número de PVs no sistema: {num_pvs}")

# ============================================================
# FUNÇÃO AUXILIAR: CONTAR TAPs NO EVENTLOG
# ============================================================

def count_tap_operations_from_eventlog(filepath, regulators=("REG1", "REG2", "REG3")):
    """
    Lê o EventLog exportado e conta quantas operações de TAP ocorreram
    para os reguladores especificados.
    """
    if not os.path.exists(filepath):
        print(f"[WARN] EventLog não encontrado: {filepath}")
        return 0

    total_taps = 0
    regs_upper = [r.upper() for r in regulators]

    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            L = line.upper()
            if "TAP" not in L:
                continue
            # verificar se é de algum regulador de interesse
            if any(reg in L for reg in regs_upper):
                total_taps += 1

    return total_taps

# ============================================================
# FUNÇÃO OBJETIVO: MINIMIZAR NÚMERO TOTAL DE TAPs
def sanitize_pf(pf_raw):
    """
    Mapeia qualquer valor real para o intervalo:
    [-1.0, -0.90] U [0.90, 1.0]
    preservando o sinal sempre que possível.
    """
    # força PF entre -1 e 1
    pf_clipped = float(np.clip(pf_raw, -1.0, 1.0))

    # módulo mínimo 0.90, máximo 1.0
    mag = abs(pf_clipped)

    if mag < 0.90:
        mag = 0.90
    elif mag > 1.0:
        mag = 1.0

    # se PF foi exatamente zero, escolha +0.90 por convenção
    if mag == 0:
        return 1

    return np.sign(pf_clipped) * mag




def target_function_taps(pf_vector):

    # ---------------------------------------------------------
    # 1) Executa caso base (PF=1) — referência
    # ---------------------------------------------------------
    dss.text(f"compile [{dss_file}]")
    dss.text("set voltagebases=[115, 4.16, 0.48]")
    dss.text("calcvoltagebases")
    dss.text("set controlmode=STATIC")

    dss.pvsystems.first()
    for _ in range(num_pvs):
        dss.pvsystems.pf = 1.0
        dss.pvsystems.next()

    dss.text("set mode=daily number=2880")
    dss.solution.solve()

    event_ref = os.path.join(output_dir, "EventLog_ref_temp.csv")
    if os.path.exists(event_ref):
        os.remove(event_ref)
    dss.text(f"export eventlog {event_ref}")

    tap_ref = count_tap_operations_from_eventlog(
        event_ref, regulators=("Reg1", "Reg2", "Reg3")
    )

    # ---------------------------------------------------------
    # 2) Executa FPA com o PF proposto
    # ---------------------------------------------------------
    dss.text(f"compile [{dss_file}]")
    dss.text("set voltagebases=[115, 4.16, 0.48]")
    dss.text("calcvoltagebases")
    dss.text("set controlmode=STATIC")

    dss.pvsystems.first()
    for pf_raw in pf_vector:
        pf = sanitize_pf(pf_raw)
        dss.pvsystems.pf = float(pf)
        dss.pvsystems.next()

    dss.text("set mode=daily number=2880")
    dss.solution.solve()

    if os.path.exists(eventlog_temp):
        os.remove(eventlog_temp)
    dss.text(f"export eventlog {eventlog_temp}")

    tap_fpa = count_tap_operations_from_eventlog(
        eventlog_temp, regulators=("Reg1", "Reg2", "Reg3")
    )

    # ---------------------------------------------------------
    # 3) Comparação simples (estilo Fibonacci no seu exemplo)
    # ---------------------------------------------------------
    if tap_fpa > tap_ref:
        # solução pior: rejeita
        return 1e9

    # caso FPA seja igual ou melhor
    return float(tap_fpa)


# ============================================================
# LEVY FLIGHT (FPA)
# ============================================================

def levy_flight(beta=1.5):
    r1 = random.random()
    r2 = random.random()
    sig_num = gamma(1 + beta) * np.sin(np.pi * beta / 2)
    sig_den = gamma((1 + beta) / 2) * beta * 2 ** ((beta - 1) / 2)
    sigma = (sig_num / sig_den) ** (1 / beta)
    return (0.01 * r1 * sigma) / (abs(r2) ** (1 / beta))

# ============================================================
# IMPLEMENTAÇÃO DO FLOWER POLLINATION ALGORITHM (FPA)
# ============================================================

def flower_pollination_algorithm(flowers, min_values, max_values,
                                 iterations, gama, lamb, p, target_function):
    """
    flowers: tamanho da população
    min_values, max_values: vetores com limites inferiores/superiores de cada variável
    iterations: número de iterações
    gama, lamb, p: parâmetros do FPA
    target_function: função-objetivo que recebe um vetor de decisão
    """
    n = len(min_values)
    pos = np.zeros((flowers, n + 1))

    # População inicial
    for i in range(flowers):
        for j in range(n):
            pos[i, j] = random.uniform(min_values[j], max_values[j])
        pos[i, -1] = target_function(pos[i, :-1])

    best = pos[pos[:, -1].argmin()].copy()

    for it in range(iterations):
        for i in range(flowers):
            if random.random() < p:
                # polinização global
                x = pos[i, :-1] + gama * levy_flight(lamb) * (best[:-1] - pos[i, :-1])
            else:
                # polinização local
                a, b = np.random.choice(flowers, 2, replace=False)
                x = pos[i, :-1] + random.random() * (pos[a, :-1] - pos[b, :-1])

            # aplicar limites
            x = np.clip(x, min_values, max_values)

            fx = target_function(x)

            if fx < pos[i, -1]:
                pos[i, :-1] = x
                pos[i, -1] = fx
                if fx < best[-1]:
                    best[:-1] = x
                    best[-1] = fx

        print(f"Iteração {it+1}: Melhor FO (nº TAPs) = {best[-1]:.2f}")

    return best

# ============================================================
# EXECUÇÃO DO FPA PARA O DIA INTEIRO (MINIMIZAR TAPs)
# ============================================================

# limites de PF (ex.: entre 0.90 e 1.00 indutivo)
min_pf = [-1.0] * num_pvs
max_pf = [1.00] * num_pvs

best = flower_pollination_algorithm(
    flowers=100,
    min_values=min_pf,
    max_values=max_pf,
    iterations=100,      # aumente depois (por enquanto pequeno p/ testar)
    gama=0.1,
    lamb=1.5,
    p=0.75,
    target_function=target_function_taps,
)

print("\n================ RESULTADO FINAL FPA =================")
print("Melhor vetor de PF encontrado (já sanitizado):")
for i, pf_raw in enumerate(best[:-1], start=1):
    pf = sanitize_pf(pf_raw)
    print(f"  PV_{i}: pf = {pf:.4f}")
print(f"Número total de TAPs (FO) = {best[-1]:.2f}")


# ============================================================
# OPCIONAL: RE-RODAR DIA COM OS PF ÓTIMOS E EXPORTAR EVENTLOG
#          + TENSÕES PARA ANÁLISE
# ============================================================

# Recompila e aplica PF "ótimos"
dss.text(f"compile [{dss_file}]")
dss.text("set voltagebases=[115, 4.16, 0.48]")
dss.text("calcvoltagebases")
dss.text("set controlmode=STATIC")

dss.pvsystems.first()
for pf_raw in best[:-1]:
    pf = sanitize_pf(pf_raw)
    dss.pvsystems.pf = float(pf)
    dss.pvsystems.next()

dss.text("set mode=daily number=2880")
dss.solution.solve()

# Exportar EventLog com PF ótimo
eventlog_opt = os.path.join(output_dir, "EventLog_PF_otimo.csv")
if os.path.exists(eventlog_opt):
    os.remove(eventlog_opt)
dss.text(f"export eventlog {eventlog_opt}")

print(f"\nEventLog com PF ótimo exportado em:\n{eventlog_opt}")
print(f"TAPs totais com PF ótimo: {count_tap_operations_from_eventlog(eventlog_opt)}")

# ============================================================
# EXPORTAR PFs ÓTIMOS PARA CSV
# ============================================================

pf_raw_list = best[:-1]                  # PFs encontrados pelo FPA (antes da sanitização)
pf_clean_list = [sanitize_pf(pf) for pf in pf_raw_list]   # PFs já tratados (sanitizados)

pv_names = []
dss.pvsystems.first()
for _ in range(num_pvs):
    pv_names.append(dss.pvsystems.name)
    dss.pvsystems.next()

df_pf = pd.DataFrame({
    "PV_Name": pv_names,
    "PF_raw": pf_raw_list,
    "PF_sanitized": pf_clean_list
})

pf_output_path = os.path.join(output_dir, "PF_otimos_FPA.csv")
df_pf.to_csv(pf_output_path, index=False)

print("\nArquivo com PFs ótimos salvo em:")
print(pf_output_path)
print(df_pf)
