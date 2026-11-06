#! /bin/env python3
"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
"""

import sys
import argparse
import re

def modifier_retained_switch(
    fichier_entree,
    fichier_sortie=None,
    id_substations=None,
    id_voltage_levels=None,
    types_switch=None,
    nouvelle_valeur="true"
):
    """
    Modifie l'attribut 'retained' des seuls switches (ou breaker/disconnector)
    en traitant le fichier comme un flux de texte.
    Respecte le format original du fichier.
    """
    cible_sauvegarde = fichier_sortie if fichier_sortie else fichier_entree

    try:
        with open(fichier_entree, 'r', encoding='utf-8') as f:
            contenu = f.read()

        compteur_modifications = 0

        # Pattern global pour capturer une substation complète (avec son contenu)
        # On utilise [^>]*? pour capturer les attributs et [\s\S]*? pour le contenu interne (multiligne)
        pattern_substation = r'(<[\w:]*substation\b[^>]*?id=["\'](.*?)["\'][^>]*?>)([\s\S]*?)(</[\w:]*substation>)'

        def repl_substation(match_sub):
            nonlocal compteur_modifications
            sub_open, sub_id, sub_content, sub_close = match_sub.groups()

            # Filtre Substation
            if id_substations and sub_id not in id_substations:
                return match_sub.group(0) # On renvoie inchangé

            # Pattern pour capturer un voltageLevel dans cette substation
            pattern_vl = r'(<[\w:]*voltageLevel\b[^>]*?id=["\'](.*?)["\'][^>]*?>)([\s\S]*?)(</[\w:]*voltageLevel>)'

            def repl_vl(match_vl):
                nonlocal compteur_modifications
                vl_open, vl_id, vl_content, vl_close = match_vl.groups()

                # Filtre VoltageLevel
                if id_voltage_levels and vl_id not in id_voltage_levels:
                    return match_vl.group(0)

                # Pattern pour capturer les balises switches valides (switch, breaker, disconnector)
                # Gère les balises auto-fermantes (/>) ou avec fermeture classique (>)
                pattern_switch = r'(<[\w:]*(?:switch|breaker|disconnector)\b[^>]*?)(/?>)'

                def repl_switch(match_sw):
                    nonlocal compteur_modifications
                    sw_body, sw_end = match_sw.groups()

                    # Extraction du type (kind) pour le filtre
                    match_kind = re.search(r'\bkind\s*=\s*["\'](.*?)["\']', sw_body)
                    sw_kind = match_kind.group(1) if match_kind else None

                    # Filtre Type/Kind de Switch
                    if types_switch and sw_kind not in types_switch:
                        return match_sw.group(0)

                    # Modification ou insertion de l'attribut 'retained'
                    pattern_retained = r'(\bretained\s*=\s*["\'])(.*?)(["\'])'
                    if re.search(pattern_retained, sw_body):
                        # L'attribut existe, on remplace sa valeur
                        nouveau_body = re.sub(pattern_retained, rf'\1{nouvelle_valeur}\3', sw_body)
                    else:
                        # L'attribut n'existe pas, on l'ajoute juste avant la fin de la balise ouvrante
                        # En préservant l'espace s'il y en a un avant '/>'
                        if sw_body.endswith(' '):
                            nouveau_body = sw_body + f'retained="{nouvelle_valeur}"'
                        else:
                            nouveau_body = sw_body + f' retained="{nouvelle_valeur}"'

                    if nouveau_body != sw_body:
                        compteur_modifications += 1
                        # Optionnel : Récupérer un ID pour le log s'il existe
                        match_id = re.search(r'\bid\s*=\s*["\'](.*?)["\']', sw_body)
                        sw_id = match_id.group(1) if match_id else "Inconnu"
                        print(f"[Modifié] Switch ID: {sw_id} | Kind: {sw_kind or 'N/A'}")

                    return nouveau_body + sw_end

                # Appliquer la modification sur les switches de ce VoltageLevel
                nouveau_vl_content = re.sub(pattern_switch, repl_switch, vl_content)
                return vl_open + nouveau_vl_content + vl_close

            # Appliquer la modification sur les VoltageLevels de cette Substation
            nouveau_sub_content = re.sub(pattern_vl, repl_vl, sub_content)
            return sub_open + nouveau_sub_content + sub_close

        # Lancement de la substitution en cascade sur tout le document
        contenu_modifie = re.sub(pattern_substation, repl_substation, contenu)

        # 3. Sauvegarde (Le fichier d'origine n'a subi aucune altération de structure)
        with open(cible_sauvegarde, 'w', encoding='utf-8', newline='') as f:
            f.write(contenu_modifie)

        print(f"\nTraitement terminé. {compteur_modifications} switch(es) modifié(s).")
        if fichier_sortie:
            print(f"Fichier enregistré sous : {cible_sauvegarde}")
        else:
            print(f"Fichier modifié sur place (inplace) : {cible_sauvegarde}")

    except FileNotFoundError:
        print(f"Fichier introuvable : {fichier_entree}", file=sys.stderr)
    except Exception as e:
        print(f"Une erreur est survenue : {e}", file=sys.stderr)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Modifie l'attribut 'retained' au niveau regex textuelle pour une précision absolue sans parseur XML."
    )

    parser.add_argument("-i", "--input", required=True, help="Chemin du fichier IIDM d'entrée")
    parser.add_argument("-o", "--output", help="Chemin du fichier de sortie (Optionnel, sinon mode inplace)")
    parser.add_argument("-s", "--substations", nargs="+", help="Liste des IDs de Substation à cibler")
    parser.add_argument("-v", "--vl", nargs="+", help="Liste des IDs de VoltageLevel à cibler")
    parser.add_argument("-k", "--kinds", nargs="+", help="Liste des types/kinds de Switch à cibler")
    parser.add_argument("--valeur", choices=["true", "false"], default="true", help="Nouvelle valeur de 'retained' (défaut: true)")

    args = parser.parse_args()

    modifier_retained_switch(
        fichier_entree=args.input,
        fichier_sortie=args.output,
        id_substations=args.substations,
        id_voltage_levels=args.vl,
        types_switch=args.kinds,
        nouvelle_valeur=args.valeur
    )