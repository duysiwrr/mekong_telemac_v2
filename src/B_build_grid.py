#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
B_build_grid.py — GIAI ĐOẠN B: SINH LƯỚI MASCARET (geometrie + xcas + loi)

CÓ SPLIT nhánh cha tại điểm hợp lưu (bắt buộc — TELEMAC không cho nhánh con
cắm vào GIỮA bief; lỗi 2 error playbook).

VÍ DỤ: Tien có VamNao@32675, CoChien@124961, HamLuong@152856, Cua@189512
  -> Tien cắt thành 4 bief.

DÙNG:
  python3 src/B_build_grid.py --subset backbone
  cd output/grid/backbone && mascaret.py mascaret.xcas
"""
import argparse
import csv
import math
import re
import sys
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.config import CFG

import numpy as np

try:
    import mikeio1d
except Exception:
    mikeio1d = None

OFFSET = CFG.MASC.OFFSET
CTOL = 60.0

# variablesStockees: 41 giá trị — COPY ĐÚNG từ file mẫu đã chạy FIN CORRECTE
# (Z, Q, ... vị trí true quyết định biến nào ghi ra .opt)
VAR_STOCK = ("true false false false false true true true false false false false "
             "false false false false false false false true false false true false "
             "false false false false false false false false false false false false "
             "false false false false false")

# Tên ĐÃ XÁC NHẬN từ ledger. "Ham Luong" có dấu cách.
# Ba Lai bỏ: cắm vào "Giao Hoa" (ngoài backbone) -> sẽ cô lập.
BACKBONE = ["Tien", "BASSAC", "VamNao", "CoChien", "Ham Luong",
            "CuaTieu", "CuaDai", "CuaCoChien", "CuaCungHau", "CuaDinhAn",
            "CuaTranDe"]


def norm(s):
    return re.sub(r"[^A-Za-z0-9]", "", str(s)).upper()


def ascii_safe(s):
    return re.sub(r"[^A-Za-z0-9_]", "_", str(s))


def load_mike(subset_names):
    text = Path(CFG.DATA.NWK11).read_text(encoding="utf-8", errors="replace")
    out = {}
    for block in re.split(r"\[branch\]", text)[1:]:
        end = block.find("EndSect  // branch")
        bt = block[:end] if end != -1 else block
        dm = re.search(
            r"definitions\s*=\s*'([^']*)'\s*,\s*'[^']*'\s*,\s*([\-\d.e]+)\s*,\s*([\-\d.e]+)", bt)
        if not dm:
            continue
        nm = dm.group(1)
        if nm not in subset_names:
            continue
        cm = re.search(
            r"connections\s*=\s*'([^']*)'\s*,\s*([\-\d.e]+)\s*,\s*'([^']*)'\s*,\s*([\-\d.e]+)", bt)
        us = ds = None
        if cm:
            if cm.group(1):
                us = (cm.group(1), float(cm.group(2)))
            if cm.group(3):
                ds = (cm.group(3), float(cm.group(4)))
        try:
            cs, ce = float(dm.group(2)), float(dm.group(3))
        except ValueError:
            continue
        if nm in out:
            out[nm]["ch_start"] = min(out[nm]["ch_start"], cs)
            out[nm]["ch_end"] = max(out[nm]["ch_end"], ce)
            out[nm]["us"] = out[nm]["us"] or us
            out[nm]["ds"] = ds or out[nm]["ds"]
        else:
            out[nm] = {"ch_start": cs, "ch_end": ce, "us": us, "ds": ds}
    return out


def get_cross_sections(path):
    if mikeio1d is None:
        sys.exit("THIẾU mikeio1d")
    xns = mikeio1d.open(str(path))
    df = xns.to_dataframe().reset_index()
    res = defaultdict(list)
    for _, row in df.iterrows():
        try:
            raw = row["cross_section"].raw
            if raw is None or len(raw) < 2:
                continue
            res[norm(row["location_id"])].append((float(row["chainage"]), raw))
        except Exception:
            continue
    for k in res:
        res[k].sort(key=lambda t: t[0])
    return res


def build_biefs(mike):
    cuts = defaultdict(set)
    for nm, b in mike.items():
        for conn in (b["us"], b["ds"]):
            if conn and conn[0] in mike:
                cha, ch = conn
                pb = mike[cha]
                if pb["ch_start"] + CTOL < ch < pb["ch_end"] - CTOL:
                    cuts[cha].add(round(ch, 1))
    biefs, bief_of, num = [], defaultdict(list), 1
    for nm in sorted(mike):
        b = mike[nm]
        bounds = [b["ch_start"]] + sorted(cuts.get(nm, set())) + [b["ch_end"]]
        merged = [bounds[0]]
        for c in bounds[1:]:
            if c - merged[-1] > CTOL:
                merged.append(c)
        for i in range(len(merged) - 1):
            ch0, ch1 = merged[i], merged[i + 1]
            biefs.append({"num": num, "ten": nm, "ch0": ch0, "ch1": ch1})
            bief_of[nm].append((num, ch0, ch1))
            num += 1
    return biefs, bief_of


def find_bief_at(bief_of, ten, ch, which):
    for (num, ch0, ch1) in bief_of.get(ten, []):
        if which == "debut" and abs(ch0 - ch) <= CTOL:
            return num
        if which == "fin" and abs(ch1 - ch) <= CTOL:
            return num
    return None


def build_nodes(mike, bief_of):
    extrem, e = {}, 1
    for nm in sorted(bief_of):
        for (num, ch0, ch1) in bief_of[nm]:
            extrem[num] = (e, e + 1)
            e += 2
    groups = defaultdict(set)
    # nội bộ nhánh
    for nm in sorted(bief_of):
        lst = sorted(bief_of[nm], key=lambda t: t[1])
        for i in range(len(lst) - 1):
            key = (nm, round(lst[i][2], 1))
            groups[key].add(extrem[lst[i][0]][1])
            groups[key].add(extrem[lst[i + 1][0]][0])
    # nhánh con -> cha
    for nm, b in mike.items():
        for end, conn in (("us", b["us"]), ("ds", b["ds"])):
            if not conn or conn[0] not in mike:
                continue
            cha, ch = conn
            key = (cha, round(ch, 1))
            lst = sorted(bief_of[nm], key=lambda t: t[1])
            child_e = extrem[lst[0][0]][0] if end == "us" else extrem[lst[-1][0]][1]
            groups[key].add(child_e)
            nf = find_bief_at(bief_of, cha, ch, "fin")
            nd = find_bief_at(bief_of, cha, ch, "debut")
            if nf:
                groups[key].add(extrem[nf][1])
            if nd:
                groups[key].add(extrem[nd][0])
    nodes = [sorted(v) for k, v in sorted(groups.items()) if len(v) >= 2]
    used = set()
    for g in nodes:
        used.update(g)
    free = []
    for (d, f) in extrem.values():
        if d not in used:
            free.append(d)
        if f not in used:
            free.append(f)
    return nodes, extrem, sorted(free)


def write_profil(f, bname, pname, absc, raw):
    f.write(f"PROFIL {bname} {ascii_safe(pname)} {absc:.1f}\n")
    ys = np.array(raw["x"].values, dtype=float)
    zs = np.array(raw["z"].values, dtype=float)
    o = np.argsort(ys)
    ys, zs = ys[o], zs[o]
    for i in range(1, len(ys)):
        if ys[i] <= ys[i - 1]:
            ys[i] = ys[i - 1] + 0.01
    for i in range(len(ys)):
        f.write(f"{ys[i]:.2f} {zs[i]:.3f} B\n")


def build_geometrie(outdir, biefs, xsecs):
    info, tot = {}, 0
    with open(outdir / "geometrie", "w", encoding=CFG.MASC.ENC_GEO) as f:
        for b in biefs:
            num, ten, ch0, ch1 = b["num"], b["ten"], b["ch0"], b["ch1"]
            cs = xsecs.get(norm(ten), [])
            sel = [(ch, raw) for ch, raw in cs if ch0 - 1 <= ch <= ch1 + 1]
            if len(sel) < 2 and cs:
                mid = 0.5 * (ch0 + ch1)
                near = sorted(cs, key=lambda t: abs(t[0] - mid))[:1]
                if len(sel) == 0 and near:
                    sel = [(ch0, near[0][1]), (ch1, near[0][1])]
                elif len(sel) == 1:
                    other = ch1 if abs(sel[0][0] - ch0) < abs(sel[0][0] - ch1) else ch0
                    sel = sorted(sel + [(other, sel[0][1])], key=lambda t: t[0])
            sel.sort(key=lambda t: t[0])
            base = (num - 1) * OFFSET
            last, n, first = None, 0, None
            for ch, raw in sel:
                a = base + (ch - ch0)
                if last is not None and a <= last + 1.0:
                    a = last + 1.0
                write_profil(f, f"Bief_{num}", f"{ten}_{int(ch)}", a, raw)
                if first is None:
                    first = a          # abscissa PROFIL ĐẦU THẬT
                last, n, tot = a, n + 1, tot + 1
            # a0/a1 = abscissa PROFIL đầu/cuối THẬT (MASCARET yêu cầu abscDebut
            # nằm trong [absc đầu, absc cuối] của các PROFIL bief đó)
            info[num] = {"ten": ten, "nprof": n,
                         "a0": first if first is not None else base,
                         "a1": last if last is not None else base + 1.0}
    return info, tot


def make_bnd_map(free_ext, extrem, biefs):
    by_num = {b["num"]: b for b in biefs}
    owner = {}
    for num, (d, f) in extrem.items():
        owner[d] = (num, "debut")
        owner[f] = (num, "fin")
    out = {}
    for x in free_ext:
        num, side = owner[x]
        ten = by_num[num]["ten"]
        nn = norm(ten)
        if nn == norm("Tien") and side == "debut":
            out[x] = {"nom": "Q_TanChau", "type": 1, "fichier": "Q_TanChau.loi"}
        elif nn == norm("BASSAC") and side == "debut":
            out[x] = {"nom": "Q_ChauDoc", "type": 1, "fichier": "Q_ChauDoc.loi"}
        else:
            a = ascii_safe(ten)
            out[x] = {"nom": f"Z_{a}_{x}", "type": 2, "fichier": f"Z_{a}_{x}.loi"}
    return out


def write_loi_files(outdir, bnd_map, hours=24):
    for x, b in bnd_map.items():
        with open(outdir / b["fichier"], "w", encoding=CFG.MASC.ENC_ASCII) as f:
            if b["type"] == 1:
                f.write(f"# {b['nom']} (tam - hang so)\n# Temps(S) Debit\n S\n")
                q = 12000.0 if "TanChau" in b["nom"] else 4000.0
                for h in range(hours + 1):
                    f.write(f" {h*3600:.3f} {q:.3f}\n")
            else:
                f.write(f"# {b['nom']} (tam - trieu sin)\n# Temps(S) Cote\n S\n")
                for h in range(hours + 1):
                    z = 1.0 + 1.2 * math.sin(2 * math.pi * h / 12.4)
                    f.write(f" {h*3600:.3f} {z:.3f}\n")


def write_xcas(outdir, biefs, info, nodes, extrem, free_ext, bnd_map, nprof):
    nb = len(biefs)
    nums = " ".join(str(b["num"]) for b in biefs)
    a_deb = " ".join(f"{info[b['num']]['a0']:.1f}" for b in biefs)
    a_fin = " ".join(f"{info[b['num']]['a1']:.1f}" for b in biefs)
    e_deb = " ".join(str(extrem[b["num"]][0]) for b in biefs)
    e_fin = " ".join(str(extrem[b["num"]][1]) for b in biefs)
    node_xml = ""
    for g in nodes:
        pad = list(g) + [0] * max(0, 5 - len(g))
        node_xml += ("          <noeud>\n            <num>"
                     + " ".join(str(x) for x in pad) + "</num>\n          </noeud>\n")
    nfree = len(free_ext)
    fnums = " ".join(str(i + 1) for i in range(nfree))
    fext = " ".join(str(x) for x in free_ext)
    fnames = "".join(f"          <string>{bnd_map[x]['nom']}</string>\n" for x in free_ext)
    ftypes = " ".join(str(bnd_map[x]["type"]) for x in free_ext)
    flois = " ".join(str(i + 1) for i in range(nfree))
    lois = "".join(f"""        <structureParametresLoi>
          <nom>{bnd_map[x]['nom']}</nom>
          <type>{bnd_map[x]['type']}</type>
          <donnees>
            <modeEntree>1</modeEntree>
            <fichier>{bnd_map[x]['fichier']}</fichier>
            <uniteTps>-0</uniteTps>
            <nbPoints>-0</nbPoints>
            <nbDebitsDifferents>-0</nbDebitsDifferents>
          </donnees>
        </structureParametresLoi>
""" for x in free_ext)
    conf = "".join(f"""        <structureParametresConfluent>
          <nbAffluent>{len(g)}</nbAffluent>
          <nom>Conf_{i+1}</nom>
          <abscisses>{" ".join("0.0" for _ in g)}</abscisses>
          <ordonnees>{" ".join("0.0" for _ in g)}</ordonnees>
          <angles>{" ".join("0.0" for _ in g)}</angles>
        </structureParametresConfluent>
""" for i, g in enumerate(nodes))
    K = CFG.MASC.STRICKLER
    fr_k = " ".join(f"{K:.1f}" for _ in biefs)

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<fichierCas>
  <parametresCas>
    <parametresGeneraux>
      <versionCode>{CFG.MASC.VERSION_CODE}</versionCode>
      <code>{CFG.MASC.CODE}</code>
      <fichMotsCles>mascaret.xcas</fichMotsCles>
      <dictionaire>dico.txt</dictionaire>
      <progPrincipal>princi.f</progPrincipal>
      <sauveModele>false</sauveModele>
      <fichSauvModele>net.tmp</fichSauvModele>
      <validationCode>false</validationCode>
      <typeValidation>1</typeValidation>
      <presenceCasiers>false</presenceCasiers>
      <bibliotheques>
        <bibliotheque>mascaretV5P1.a damoV3P0.a</bibliotheque>
      </bibliotheques>
    </parametresGeneraux>
    <parametresModelePhysique>
      <perteChargeConf>false</perteChargeConf>
      <compositionLits>1</compositionLits>
      <conservFrotVertical>false</conservFrotVertical>
      <elevCoteArrivFront>0.05</elevCoteArrivFront>
      <interpolLinStrickler>false</interpolLinStrickler>
      <debordement>
        <litMajeur>false</litMajeur>
        <zoneStock>false</zoneStock>
      </debordement>
    </parametresModelePhysique>
    <parametresNumeriques>
      <calcOndeSubmersion>false</calcOndeSubmersion>
      <decentrement>false</decentrement>
      <froudeLimCondLim>1000.0</froudeLimCondLim>
      <traitImplicitFrot>false</traitImplicitFrot>
      <hauteurEauMini>{CFG.MASC.H_EAU_MINI}</hauteurEauMini>
      <implicitNoyauTrans>false</implicitNoyauTrans>
      <optimisNoyauTrans>false</optimisNoyauTrans>
      <perteChargeAutoElargissement>true</perteChargeAutoElargissement>
      <termesNonHydrostatiques>false</termesNonHydrostatiques>
      <apportDebit>0</apportDebit>
      <attenuationConvection>false</attenuationConvection>
    </parametresNumeriques>
    <parametresTemporels>
      <pasTemps>{CFG.MASC.PAS_TEMPS}</pasTemps>
      <tempsInit>0.0</tempsInit>
      <critereArret>1</critereArret>
      <nbPasTemps>1</nbPasTemps>
      <tempsMax>86400.0</tempsMax>
      <pasTempsVar>false</pasTempsVar>
      <nbCourant>0.8</nbCourant>
      <coteMax>0.0</coteMax>
      <abscisseControle>0.0</abscisseControle>
      <biefControle>1</biefControle>
    </parametresTemporels>
    <parametresGeometrieReseau>
      <geometrie>
        <fichier>geometrie</fichier>
        <format>2</format>
        <profilsAbscAbsolu>true</profilsAbscAbsolu>
      </geometrie>
      <listeBranches>
        <nb>{nb}</nb>
        <numeros>{nums}</numeros>
        <abscDebut>{a_deb}</abscDebut>
        <abscFin>{a_fin}</abscFin>
        <numExtremDebut>{e_deb}</numExtremDebut>
        <numExtremFin>{e_fin}</numExtremFin>
      </listeBranches>
      <listeNoeuds>
        <nb>{len(nodes)}</nb>
        <noeuds>
{node_xml}        </noeuds>
      </listeNoeuds>
      <extrLibres>
        <nb>{nfree}</nb>
        <num>{fnums}</num>
        <numExtrem>{fext}</numExtrem>
        <noms>
{fnames}        </noms>
        <typeCond>{ftypes}</typeCond>
        <numLoi>{flois}</numLoi>
      </extrLibres>
    </parametresGeometrieReseau>
    <parametresConfluents>
      <nbConfluents>{len(nodes)}</nbConfluents>
      <confluents>
{conf}      </confluents>
    </parametresConfluents>
    <parametresPlanimetrageMaillage>
      <methodeMaillage>5</methodeMaillage>
      <planim>
        <nbPas>50</nbPas>
        <nbZones>1</nbZones>
        <valeursPas>2.0</valeursPas>
        <num1erProf>1</num1erProf>
        <numDerProf>{nprof}</numDerProf>
      </planim>
      <maillage>
        <modeSaisie>2</modeSaisie>
        <sauvMaillage>false</sauvMaillage>
        <maillageClavier>
          <nbSections>0</nbSections>
          <nbPlages>1</nbPlages>
          <num1erProfPlage>1</num1erProfPlage>
          <numDerProfPlage>{nprof}</numDerProfPlage>
          <pasEspacePlage>500.0</pasEspacePlage>
          <nbZones>0</nbZones>
        </maillageClavier>
      </maillage>
    </parametresPlanimetrageMaillage>
    <parametresSingularite>
      <nbSeuils>0</nbSeuils>
    </parametresSingularite>
    <parametresApportDeversoirs/>
    <parametresCalage>
      <frottement>
        <loi>1</loi>
        <nbZone>{nb}</nbZone>
        <numBranche>{nums}</numBranche>
        <absDebZone>{a_deb}</absDebZone>
        <absFinZone>{a_fin}</absFinZone>
        <coefLitMin>{fr_k}</coefLitMin>
        <coefLitMaj>{fr_k}</coefLitMaj>
      </frottement>
      <zoneStockage>
        <nbProfils>0</nbProfils>
        <numProfil>-0</numProfil>
        <limGauchLitMaj>-0</limGauchLitMaj>
        <limDroitLitMaj>-0</limDroitLitMaj>
      </zoneStockage>
    </parametresCalage>
    <parametresLoisHydrauliques>
      <nb>{nfree}</nb>
      <lois>
{lois}      </lois>
    </parametresLoisHydrauliques>
    <parametresConditionsInitiales>
      <repriseEtude>
        <repriseCalcul>false</repriseCalcul>
      </repriseEtude>
      <ligneEau>
        <LigEauInit>true</LigEauInit>
        <modeEntree>1</modeEntree>
        <fichLigEau>init.lig</fichLigEau>
        <formatFichLig>2</formatFichLig>
        <nbPts>-0</nbPts>
      </ligneEau>
    </parametresConditionsInitiales>
    <parametresImpressionResultats>
      <titreCalcul>Mekong DBSCL {len(biefs)} bief</titreCalcul>
      <impression>
        <impressionGeometrie>false</impressionGeometrie>
        <impressionPlanimetrage>false</impressionPlanimetrage>
        <impressionReseau>false</impressionReseau>
        <impressionLoiHydraulique>false</impressionLoiHydraulique>
        <impressionligneEauInitiale>false</impressionligneEauInitiale>
        <impressionCalcul>false</impressionCalcul>
      </impression>
      <pasStockage>
        <premPasTpsStock>1</premPasTpsStock>
        <pasStock>{CFG.MASC.PAS_STOCK}</pasStock>
        <pasImpression>100</pasImpression>
      </pasStockage>
      <resultats>
        <fichResultat>ResultatsOpthyca.opt</fichResultat>
        <postProcesseur>2</postProcesseur>
      </resultats>
      <listing>
        <fichListing>listing.lis</fichListing>
      </listing>
      <fichReprise>
        <fichRepriseEcr>net_ecr.rep</fichRepriseEcr>
      </fichReprise>
      <rubens>
        <ecartInterBranch>1.0</ecartInterBranch>
      </rubens>
      <stockage>
        <option>1</option>
        <nbSite>0</nbSite>
      </stockage>
    </parametresImpressionResultats>
    <parametresVariablesCalculees>
      <variablesCalculees>{" ".join("false" for _ in range(15))}</variablesCalculees>
    </parametresVariablesCalculees>
    <parametresVariablesStockees>
      <variablesStockees>{VAR_STOCK}</variablesStockees>
    </parametresVariablesStockees>
  </parametresCas>
</fichierCas>
"""
    (outdir / "mascaret.xcas").write_text(xml, encoding=CFG.MASC.ENC_ASCII,
                                          errors="replace")


def write_init_lig(outdir, biefs, info, xsecs):
    """Sinh init.lig — format ĐÚNG theo file mẫu đã chạy FIN CORRECTE:

      RESULTATS CALCUL,DATE : ...
      FICHIER RESULTAT MASCARET
      -----------------------------------------------------------------------
       IMAX  =  <n> NBBIEF=  <nb>
       I1,I2 = <chỉ số section đầu/cuối mỗi bief, 10 số/dòng>
       X
        <tất cả abscissa, 5 số/dòng, %13.2f>
       Z
        <tất cả mực nước, 5 số/dòng>
       Q
        <tất cả lưu lượng, 5 số/dòng>
       FIN

    SMART INIT (lỗi 7 playbook): z = max(dốc 9->3m, bed_min + 5.0)
    """
    # đáy nhỏ nhất mỗi bief
    bed = {}
    for b in biefs:
        cs = xsecs.get(norm(b["ten"]), [])
        sel = [raw for ch, raw in cs if b["ch0"] - 1 <= ch <= b["ch1"] + 1]
        if not sel and cs:
            sel = [cs[0][1]]
        zmin = 0.0
        if sel:
            try:
                zmin = min(float(min(r["z"].values)) for r in sel)
            except Exception:
                zmin = 0.0
        bed[b["num"]] = zmin

    nb = len(biefs)
    X, Z, Q = [], [], []
    i1i2 = []          # chỉ số section đầu & cuối mỗi bief (1-based)
    idx = 1
    for k, b in enumerate(biefs):
        n = info[b["num"]]["nprof"]
        if n == 0:
            continue
        a0, a1 = info[b["num"]]["a0"], info[b["num"]]["a1"]
        frac = k / max(1, nb - 1)
        z_slope = 9.0 - frac * (9.0 - 3.0)
        z_init = max(z_slope, bed[b["num"]] + 5.0)     # SÀN ĐÁY +5m
        i1i2.append(idx)
        for j in range(n):
            x = a0 + (a1 - a0) * (j / max(1, n - 1))
            X.append(x)
            Z.append(z_init)
            Q.append(5000.0)
        idx += n
        i1i2.append(idx - 1)

    imax = len(X)
    L = []
    L.append("RESULTATS CALCUL,DATE : 01/01/11 00:00")
    L.append("FICHIER RESULTAT MASCARET")
    L.append("-" * 71)
    L.append(f" IMAX  = {imax:4d} NBBIEF={nb:5d}")
    # I1,I2: 10 số/dòng, width 6
    for i in range(0, len(i1i2), 10):
        L.append(" I1,I2 =" + "".join(f"{v:6d}" for v in i1i2[i:i + 10]))

    def block(label, vals, fmt="{:13.2f}"):
        out = [f" {label}"]
        for i in range(0, len(vals), 5):
            out.append("".join(fmt.format(v) for v in vals[i:i + 5]))
        return out

    L += block("X", X)
    L += block("Z", Z)
    L += block("Q", Q)
    L.append(" FIN")
    (outdir / "init.lig").write_text("\n".join(L) + "\n",
                                     encoding=CFG.MASC.ENC_ASCII)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--subset", default="backbone",
                    choices=["backbone", "culao", "full"])
    ap.add_argument("--outdir", default=None)
    args = ap.parse_args()
    outdir = Path(args.outdir) if args.outdir else (CFG.OUT.GRID / args.subset)
    outdir.mkdir(parents=True, exist_ok=True)

    print(f"=== GĐ B — SINH LƯỚI (subset={args.subset}) ===")
    kept = set()
    with open(CFG.OUT.LEDGER / "branches.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f, delimiter=";"):
            if r["giu"] == "GIU":
                kept.add(r["ten_mike"])
    if args.subset == "full":
        sel = kept
    else:
        sel = {n for n in kept if any(norm(n) == norm(b) for b in BACKBONE)}
        if args.subset == "culao":
            with open(CFG.OUT.LEDGER / "branches.csv", encoding="utf-8") as f:
                for r in csv.DictReader(f, delimiter=";"):
                    if r["giu"] == "GIU" and r.get("co_survey2020") == "yes":
                        sel.add(r["ten_mike"])
    print(f"Tập con: {len(sel)} nhánh")

    mike = load_mike(sel)
    print(f"Connection: {len(mike)} nhánh")

    biefs, bief_of = build_biefs(mike)
    print(f"SPLIT: {len(mike)} nhánh -> {len(biefs)} bief")
    for nm in sorted(bief_of):
        if len(bief_of[nm]) > 1:
            print(f"   {nm}: {len(bief_of[nm])} bief")

    nodes, extrem, free_ext = build_nodes(mike, bief_of)
    print(f"Nút: {len(nodes)} | extremité tự do: {len(free_ext)}")

    xsecs = get_cross_sections(CFG.DATA.XNS11)
    info, nprof = build_geometrie(outdir, biefs, xsecs)
    empty = [n for n, v in info.items() if v["nprof"] < 2]
    print(f"Geometrie: {nprof} PROFIL / {len(biefs)} bief")
    if empty:
        print(f"   [!] {len(empty)} bief <2 PROFIL: {empty[:10]}")

    bnd_map = make_bnd_map(free_ext, extrem, biefs)
    print("Biên:")
    for x in free_ext:
        print(f"   ext {x}: {bnd_map[x]['nom']} (type {bnd_map[x]['type']})")

    write_xcas(outdir, biefs, info, nodes, extrem, free_ext, bnd_map, nprof)
    write_loi_files(outdir, bnd_map)
    write_init_lig(outdir, biefs, info, xsecs)
    (outdir / "FichierCas.txt").write_text("'mascaret.xcas'\n",
                                           encoding=CFG.MASC.ENC_ASCII)
    with open(outdir / "bief_map.txt", "w", encoding=CFG.MASC.ENC_ASCII) as f:
        f.write("# bief\tten\tch0\tch1\tnprof\tabsc0\tabsc1\n")
        for b in biefs:
            i = info[b["num"]]
            f.write(f"{b['num']}\t{ascii_safe(b['ten'])}\t{b['ch0']:.0f}\t"
                    f"{b['ch1']:.0f}\t{i['nprof']}\t{i['a0']:.1f}\t{i['a1']:.1f}\n")

    print(f"\n-> {outdir}/")
    print("Chạy thử:")
    print(f"  cp $(find ~/telemac -name dico.txt 2>/dev/null | head -1) {outdir}/")
    print(f"  cd {outdir} && mascaret.py mascaret.xcas")
    print("  grep -i 'FIN CORRECTE' mascaret0.lis")


if __name__ == "__main__":
    main()
