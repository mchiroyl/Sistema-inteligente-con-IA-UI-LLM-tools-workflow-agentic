from typing import Any, Dict, Optional

# ─────────────────────────────────────────────────────────────────────────────
# Corporate support policy knowledge base (emulates a real institutional DB).
# Each entry defines the priority and SLA-bound action for a keyword category.
# ─────────────────────────────────────────────────────────────────────────────
SUPPORT_POLICIES: Dict[str, Dict[str, str]] = {
    # Critical security threats
    "virus":     {"priority": "Crítica", "action": "AISLAR el equipo de la red inmediatamente. Contactar al equipo de Ciberseguridad. SLA: 30 minutos."},
    "ransomware":{"priority": "Crítica", "action": "AISLAR el equipo y apagar la red. Notificar a Dirección y Ciberseguridad. SLA: 15 minutos."},
    "hackeo":    {"priority": "Crítica", "action": "AISLAR el equipo. Escalar a Ciberseguridad y Dirección General. SLA: 30 minutos."},
    "brecha":    {"priority": "Crítica", "action": "Activar protocolo de incidentes de seguridad. Notificar a todas las áreas. SLA: 30 minutos."},
    # Infrastructure
    "servidor":  {"priority": "Crítica", "action": "Escalar inmediatamente al equipo de Infraestructura. Notificar al equipo de guardia. SLA: 1 hora."},
    "caída":     {"priority": "Crítica", "action": "Escalar a Infraestructura. Verificar estado de servicios críticos. SLA: 1 hora."},
    "caido":     {"priority": "Crítica", "action": "Escalar a Infraestructura. Verificar estado de servicios críticos. SLA: 1 hora."},
    # Hardware
    "no enciende":{"priority": "Alta",   "action": "Enviar técnico de hardware al puesto del usuario. SLA: 4 horas hábiles."},
    "pantalla":  {"priority": "Alta",    "action": "Diagnóstico remoto primero; si persiste, enviar técnico. SLA: 4 horas hábiles."},
    "no inicia": {"priority": "Alta",    "action": "Diagnóstico remoto de arranque del sistema. SLA: 4 horas hábiles."},
    "disco":     {"priority": "Alta",    "action": "Revisión de disco duro. Hacer respaldo antes de intervenir. SLA: 4 horas hábiles."},
    "teclado":   {"priority": "Media",   "action": "Sustitución de periférico. Solicitar equipo de reemplazo. SLA: 8 horas hábiles."},
    "mouse":     {"priority": "Media",   "action": "Sustitución de periférico. Solicitar equipo de reemplazo. SLA: 8 horas hábiles."},
    # Performance
    "lento":     {"priority": "Media",   "action": "Diagnóstico remoto de rendimiento (RAM, procesos, disco). SLA: 24 horas hábiles."},
    "lentitud":  {"priority": "Media",   "action": "Diagnóstico remoto de rendimiento. SLA: 24 horas hábiles."},
    # Network
    "internet":  {"priority": "Media",   "action": "Verificar configuración de red y DNS. Contactar ISP si es necesario. SLA: 8 horas hábiles."},
    "red":       {"priority": "Media",   "action": "Revisar configuración de red, switches y VPN. SLA: 8 horas hábiles."},
    "vpn":       {"priority": "Media",   "action": "Revisar credenciales y configuración de VPN corporativa. SLA: 8 horas hábiles."},
    # Software / Applications
    "correo":    {"priority": "Media",   "action": "Revisar configuración del cliente de correo y credenciales. SLA: 8 horas hábiles."},
    "email":     {"priority": "Media",   "action": "Revisar configuración del cliente de correo y credenciales. SLA: 8 horas hábiles."},
    "impresora": {"priority": "Media",   "action": "Diagnóstico de impresora: drivers, conexión y cola de impresión. SLA: 24 horas hábiles."},
    "software":  {"priority": "Media",   "action": "Diagnóstico de la aplicación. Si es licencia, verificar estado. SLA: 8 horas hábiles."},
    "aplicación":{"priority": "Media",   "action": "Diagnóstico remoto de la aplicación. SLA: 8 horas hábiles."},
    # Account / Access
    "contraseña":{"priority": "Baja",    "action": "Reset de contraseña por el administrador de sistemas. SLA: 2 horas hábiles."},
    "password":  {"priority": "Baja",    "action": "Reset de contraseña por el administrador. SLA: 2 horas hábiles."},
    "acceso":    {"priority": "Baja",    "action": "Verificar permisos y roles del usuario en el sistema. SLA: 4 horas hábiles."},
    "usuario":   {"priority": "Baja",    "action": "Gestión de cuentas de usuario. SLA: 4 horas hábiles."},
    # Installations
    "instalar":  {"priority": "Baja",    "action": "Solicitud de instalación de software. Requiere aprobación del área. SLA: 48 horas hábiles."},
    "instalación":{"priority": "Baja",   "action": "Solicitud evaluada por el equipo de TI. SLA: 48 horas hábiles."},
    "actualizar":{"priority": "Baja",    "action": "Actualización programada. Se coordinará con el usuario. SLA: 72 horas hábiles."},
}

_PRIORITY_ORDER = {"Crítica": 4, "Alta": 3, "Media": 2, "Baja": 1}
_DEFAULT_POLICY = {
    "priority": "Media",
    "action": "Asignar a técnico de soporte general. SLA: 8 horas hábiles.",
}


def check_support_policy(
    problem_description: str,
    device_or_system: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Tool 2 — Consult the institutional support policy DB.

    Searches for the highest-priority keyword match in the ticket text and
    returns the corresponding SLA-bound action.  Falls back to a default
    'Media' priority policy when no keyword matches.

    Args:
        problem_description: Description of the reported problem.
        device_or_system: Affected device/system (used in combined lookup).

    Returns:
        Dict with priority, suggested_action, matched_keyword, policy_found.
    """
    combined = f"{problem_description} {device_or_system or ''}".lower()

    best_policy = None
    best_score = 0
    best_keyword = None

    for keyword, policy in SUPPORT_POLICIES.items():
        if keyword in combined:
            score = _PRIORITY_ORDER.get(policy["priority"], 0)
            if score > best_score:
                best_score = score
                best_policy = policy
                best_keyword = keyword

    if best_policy is None:
        return {
            "priority": _DEFAULT_POLICY["priority"],
            "suggested_action": _DEFAULT_POLICY["action"],
            "matched_keyword": "general",
            "policy_found": False,
        }

    return {
        "priority": best_policy["priority"],
        "suggested_action": best_policy["action"],
        "matched_keyword": best_keyword,
        "policy_found": True,
    }
