"""
Módulo: src/limb_rules.py
Responsabilidad: Validadores de extremidades (PIE / BRA) aplicados sobre la lista de
bloques resueltos antes de concatenar el prompt. Evita colisiones visuales entre
piernas/manos declaradas por distintos bloques.

Orden de aplicación:
  1. Encuadre:    Plano Medio / Primer Plano  -> se anulan todos los PIE.
  2. Cinemática:  pose de locomoción (walking) -> se anulan los PIE de piernas cruzadas.
  3. Manos:       PIE-04 (Interaccion_Manual) ocupa la Mano 1 y los BRA solo gestionan la
                  Mano 2 (sin Primaria ni Ambas_Manos). Sin PIE-04: una sola acción primaria
                  salvo BRA 'Ambas_Manos'. Presupuesto de 2 manos y auto-asignación de
                  Soporte/Libre a la mano restante.
  4. Colisión:    si hay PIE/BRA, se retiran los tags de piernas/manos de POS/ACC/POSE_PACK/EXP.
                  Sin BRA, si un EXP trae tags de manos (EXP-05/06), éstos tienen prioridad y
                  se retiran los tags de manos de POS/ACC/POSE_PACK.
"""

import re
from typing import Any, Dict, List, Optional, Tuple

Block = Dict[str, Any]

# Bloques que definen el encuadre y la postura base
FRAMING_CATS = ("CAMERA", "CAM", "CAMARA", "POSE_PACK")
POSE_CATS = ("POSTURE", "POS", "POSTURA", "GESTURE", "ACC", "GESTO", "POSE_PACK")
# Bloques cuyos tags de manos/piernas se retiran cuando hay LEGS/HANDS (EXP-05/06 traen manos)
CLEAN_CATS = POSE_CATS + ("EXPRESSION", "EXP", "EXPRESION")
CAT_HANDS = ("HANDS", "BRA", "MANOS")
CAT_LEGS = ("LEGS", "PIE", "PIERNAS")
CAT_EXP = ("EXPRESSION", "EXP", "EXPRESION")

CLOSE_FRAMING_TAGS = re.compile(
    r"\b(upper body|close-up|portrait|waist up|medium shot|head and shoulders|"
    r"head and neck|cropped at hips|torso focus)\b", re.I)
LOCOMOTION_TAGS = re.compile(r"\b(walking|running|mid-stride|jogging)\b", re.I)
SEATED_TAGS = re.compile(r"\b(sitting|seated|leaning|lying|kneeling|reclining)\b", re.I)
CROSSED_LEGS_TAGS = re.compile(r"\bcrossed legs\b", re.I)

HAND_TAG = re.compile(r"\b(hands?|arms?|fists?|fingers?)\b", re.I)
LEG_TAG = re.compile(r"\b(legs?|knees?|wide stance|one leg)\b", re.I)

# Roles de mano y pierna (compatibilidad bilingüe inglés/español)
ROLE_PRIMARY = ("Primary_Hand", "Mano_Primaria")
ROLE_SECONDARY = ("Secondary_Hand", "Mano_Secundaria")
ROLE_SUPPORT = ("Support_Hand", "Mano_Soporte")
ROLE_FREE = ("Free_Hand", "Mano_Libre")
ROLE_BOTH = ("Both_Hands", "Ambas_Manos")
PIE_MANUAL = ("Manual_Interaction", "Interaccion_Manual")
PIE_CROSSED = ("Leg_Crossed", "Pierna_Cruzada")

# Al exceder 2 manos se descarta primero lo de menor prioridad
DROP_PRIORITY = (ROLE_FREE, ROLE_SUPPORT, ROLE_SECONDARY)


def _tags(block: Block) -> List[str]:
    return [t.strip() for t in block.get("Prompt_Positivo", "").split(",") if t.strip()]


def _any_tag(blocks: List[Block], pattern: re.Pattern) -> bool:
    return any(pattern.search(t) for b in blocks for t in _tags(b))


def _has_role(block: Block, role: Any) -> bool:
    tb = block.get("Tipo_Bloque")
    if isinstance(role, (tuple, list, set)):
        return tb in role
    return tb == role


def _is_interaction(block: Block) -> bool:
    return (block["Categoria"] in CAT_HANDS and _has_role(block, ROLE_PRIMARY)) or \
           (block["Categoria"] in CAT_LEGS and _has_role(block, PIE_MANUAL))


def _occupies_hand(block: Block) -> bool:
    if block["Categoria"] in CAT_HANDS:
        return not _has_role(block, ROLE_BOTH)
    return block["Categoria"] in CAT_LEGS and _has_role(block, PIE_MANUAL)


class LimbRuleEngine:
    """Aplica las reglas condicionales de extremidades sobre una lista de bloques."""

    def __init__(self, db: Any):
        self.db = db

    def apply(self, blocks: List[Block]) -> Tuple[List[Block], List[str]]:
        notes: List[str] = []
        blocks = self._dedupe(blocks)
        blocks = self._rule_framing(blocks, notes)
        blocks = self._rule_locomotion(blocks, notes)
        blocks = self._rule_hands(blocks, notes)
        blocks = self._rule_tag_collisions(blocks, notes)
        return blocks, notes

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _dedupe(blocks: List[Block]) -> List[Block]:
        seen, out = set(), []
        for b in blocks:
            if b["ID"] in seen:
                continue
            seen.add(b["ID"])
            out.append(b)
        return out

    def _default_for_role(self, role: Any) -> Optional[Block]:
        pool = self.db.get_entries_by_cat("HANDS") or self.db.get_entries_by_cat("MANOS") or self.db.get_entries_by_cat("BRA")
        return next((b for b in pool if _has_role(b, role)), None)

    # -------------------------------------------------------------------- rules
    def _rule_framing(self, blocks: List[Block], notes: List[str]) -> List[Block]:
        framing = [b for b in blocks if b["Categoria"] in FRAMING_CATS]
        pies = [b for b in blocks if b["Categoria"] in CAT_LEGS]
        if pies and _any_tag(framing, CLOSE_FRAMING_TAGS):
            ids = ", ".join(b["ID"] for b in pies)
            notes.append(f"Encuadre cerrado (Plano Medio/Primer Plano): piernas anuladas ({ids}).")
            return [b for b in blocks if b["Categoria"] not in CAT_LEGS]
        return blocks

    def _rule_locomotion(self, blocks: List[Block], notes: List[str]) -> List[Block]:
        poses = [b for b in blocks if b["Categoria"] in POSE_CATS]
        if not _any_tag(poses, LOCOMOTION_TAGS):
            return blocks
        out = []
        for b in blocks:
            crossed = b["Categoria"] in CAT_LEGS and (
                _has_role(b, PIE_CROSSED) or _any_tag([b], CROSSED_LEGS_TAGS))
            if crossed:
                notes.append(f"Pose de locomoción: {b['ID']} (piernas cruzadas) anulado.")
                continue
            out.append(b)
        return out

    def _rule_hands(self, blocks: List[Block], notes: List[str]) -> List[Block]:
        manual = next((b for b in blocks if b["Categoria"] in CAT_LEGS
                       and _has_role(b, PIE_MANUAL)), None)
        if manual:
            blocks = self._reserve_hand_one(blocks, manual, notes)

        both = any(b["Categoria"] in CAT_HANDS and _has_role(b, ROLE_BOTH) for b in blocks)
        interactions = [b for b in blocks if _is_interaction(b)]

        # Una sola acción de interacción salvo petición explícita ('Both_Hands')
        if len(interactions) > 1 and not both:
            keep = interactions[0]
            ambas_id = next((b["ID"] for b in (self.db.get_entries_by_cat("HANDS") or self.db.get_entries_by_cat("MANOS") or self.db.get_entries_by_cat("BRA"))
                             if _has_role(b, ROLE_BOTH)), "HAND-BOTH")
            for extra in interactions[1:]:
                notes.append(f"Dos acciones de interacción simultáneas: se conserva {keep['ID']}, "
                             f"se elimina {extra['ID']} (use {ambas_id} para pedir ambas manos).")
            drop = {b["ID"] for b in interactions[1:]}
            blocks = [b for b in blocks if b["ID"] not in drop]
            interactions = [keep]

        if both:
            if not interactions:
                notes.append("Modificador 'Both_Hands' sin acción primaria: modificador ignorado.")
                return [b for b in blocks if not _has_role(b, ROLE_BOTH) or b["Categoria"] not in CAT_HANDS]
            # Ambas manos ocupadas por la acción primaria: no queda mano para otros roles
            busy = [b for b in blocks if b["Categoria"] in CAT_HANDS and
                    (_has_role(b, ROLE_SECONDARY) or _has_role(b, ROLE_SUPPORT) or _has_role(b, ROLE_FREE))]
            for b in busy:
                notes.append(f"Ambas manos en acción primaria: {b['ID']} eliminado.")
            busy_ids = {b["ID"] for b in busy}
            return [b for b in blocks if b["ID"] not in busy_ids]

        # Presupuesto de 2 manos
        hand_blocks = [b for b in blocks if _occupies_hand(b)]
        while len(hand_blocks) > 2:
            victim = next((b for role in DROP_PRIORITY for b in reversed(hand_blocks)
                           if b["Categoria"] in CAT_HANDS and _has_role(b, role)), hand_blocks[-1])
            notes.append(f"Más de dos manos declaradas: {victim['ID']} eliminado.")
            blocks = [b for b in blocks if b["ID"] != victim["ID"]]
            hand_blocks = [b for b in hand_blocks if b["ID"] != victim["ID"]]

        # Auto-asignación de la mano restante
        if interactions and len(hand_blocks) == 1:
            poses = [b for b in blocks if b["Categoria"] in POSE_CATS]
            role = ROLE_SUPPORT if _any_tag(poses, SEATED_TAGS) else ROLE_FREE
            filler = self._default_for_role(role)
            if filler:
                anchor = blocks.index(interactions[0])
                blocks = blocks[:anchor + 1] + [filler] + blocks[anchor + 1:]
                label = "Support" if role == ROLE_SUPPORT else "Free"
                notes.append(f"Mano restante auto-asignada como {label}: {filler['ID']}.")
        return blocks

    @staticmethod
    def _reserve_hand_one(blocks: List[Block], manual: Block, notes: List[str]) -> List[Block]:
        """
        Interaccion_Manual en piernas ocupa la Mano 1. Las manos solo gestionan la Mano 2:
        - 'Both_Hands' es imposible (solo queda una mano) -> se elimina.
        - 'Primary_Hand' sería una segunda interacción simultánea -> se elimina.
        El resto (Secundaria / Soporte / Libre) compite por la Mano 2 en el presupuesto.
        """
        out = []
        for b in blocks:
            if b["Categoria"] in CAT_HANDS and _has_role(b, ROLE_BOTH):
                notes.append(f"Mano 1 ocupada por {manual['ID']}: {b['ID']} (ambas manos) eliminado.")
                continue
            if b["Categoria"] in CAT_HANDS and _has_role(b, ROLE_PRIMARY):
                notes.append(f"Mano 1 ocupada por {manual['ID']}: {b['ID']} (acción primaria) "
                             f"eliminado; la Mano 2 solo admite Secundaria/Soporte/Libre.")
                continue
            out.append(b)
        return out

    def _rule_tag_collisions(self, blocks: List[Block], notes: List[str]) -> List[Block]:
        has_pie = any(b["Categoria"] in CAT_LEGS for b in blocks)
        has_bra = any(b["Categoria"] in CAT_HANDS for b in blocks) or \
            any(b["Categoria"] in CAT_LEGS and _has_role(b, PIE_MANUAL) for b in blocks)
        # Sin HANDS: las manos declaradas en EXPRESSION tienen prioridad sobre las de la pose
        exp_hands = not has_bra and _any_tag(
            [b for b in blocks if b["Categoria"] in CAT_EXP], HAND_TAG)
        if not (has_pie or has_bra or exp_hands):
            return blocks

        out = []
        for b in blocks:
            if b["Categoria"] not in CLEAN_CATS:
                out.append(b)
                continue
            strip_hands = has_bra or (exp_hands and b["Categoria"] in POSE_CATS)
            kept, removed = [], []
            for t in _tags(b):
                if (strip_hands and HAND_TAG.search(t)) or (has_pie and LEG_TAG.search(t)):
                    removed.append(t)
                else:
                    kept.append(t)
            if removed:
                source = ("extremidades (HANDS/LEGS)" if has_bra else
                          "LEGS y las manos de EXP" if (has_pie and exp_hands) else
                          "LEGS" if has_pie else "las manos de EXP")
                notes.append(f"{b['ID']}: tags de extremidades sustituidos por {source} ({', '.join(removed)}).")
            if not kept:
                continue  # bloque vacío
            if removed:
                b = {**b, "Prompt_Positivo": ", ".join(kept)}
            out.append(b)
        return out
