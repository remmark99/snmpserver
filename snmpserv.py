# import asyncio
# from pysnmp.entity import engine, config
# from pysnmp.carrier.asyncio.dgram import udp
# from pysnmp.entity.rfc3413 import ntfrcv

# ENGINE_HEX = "80001F880382B668448AF6"  # engineID устройства БЕЗ "0x"
# USER = "test"
# AUTH_PASS = "qwe12345"
# PRIV_PASS = "qwe12345"  # если без шифрования — см. ниже

# snmpEngine = engine.SnmpEngine()

# config.add_v1_system(snmpEngine, 'v2c-area', 'public')  # поменяй community на реальную

# # UDP/1162 listener
# config.add_transport(
#     snmpEngine,
#     udp.DOMAIN_NAME,
#     udp.UdpTransport().open_server_mode(("0.0.0.0", 1162))
# )

# # SNMPv3 user (привязка к engineID устройства)
# config.add_v3_user(
#     snmpEngine,
#     USER,
#     config.USM_AUTH_HMAC96_SHA,
#     AUTH_PASS,
#     config.USM_PRIV_CFB128_AES,
#     PRIV_PASS,
#     securityEngineId=bytes.fromhex(ENGINE_HEX),
# )

# def on_trap(snmpEngine, stateReference, contextEngineId, contextName, varBinds, cbCtx):
#     print("trap")
#     # Попробуем достать адрес отправителя
#     try:
#         tr = snmpEngine.msgAndPduDsp.getTransportInfo(stateReference)  # может отличаться по версиям
#         peer = tr[1]  # (ip, port)
#     except Exception:
#         peer = ("?", "?")

#     print(f"\n=== TRAP from {peer[0]}:{peer[1]} ===")
#     for oid, val in varBinds:
#         print(f"{oid.prettyPrint()} = {val.prettyPrint()}")

# ntfrcv.NotificationReceiver(snmpEngine, on_trap)

# # Запуск dispatcher (asyncio)
# snmpEngine.transport_dispatcher.job_started(1)
# snmpEngine.transport_dispatcher.run_dispatcher()

import os
from pysnmp.entity import engine, config
from pysnmp.carrier.asyncio.dgram import udp
from pysnmp.entity.rfc3413 import ntfrcv
from pysnmp import debug

print("start")

# --- Settings (env-friendly) ---
LISTEN_HOST = os.getenv("LISTEN_HOST", "0.0.0.0")
LISTEN_PORT = int(os.getenv("LISTEN_PORT", "1162"))

# Enable verbose debug if needed: DEBUG_SNMP=1
if os.getenv("DEBUG_SNMP") == "1":
    debug.set_logger(debug.Debug("all"))

snmpEngine = engine.SnmpEngine()

# Transport: UDP listener
config.add_transport(
    snmpEngine,
    udp.DOMAIN_NAME,
    udp.UdpTransport().open_server_mode((LISTEN_HOST, LISTEN_PORT)),
)

# --- Accept SNMPv1/v2c communities ---
# You must list communities you want to accept.
# Put the real ones in env: COMMUNITIES="public,private,whatever"
communities = [c.strip() for c in os.getenv("COMMUNITIES", "public").split(",") if c.strip()]
for comm in communities:
    config.add_v1_system(snmpEngine, f"v2c-{comm}", comm)

# --- Accept SNMPv3 users (optional) ---
# Put users in env if you need v3:
# V3_USERS="user1:SHA:authpass:AES:privpass,user2:SHA:authpass"
# Formats supported:
#   user:AUTH_PROTO:AUTH_PASS
#   user:AUTH_PROTO:AUTH_PASS:PRIV_PROTO:PRIV_PASS
# AUTH_PROTO: MD5|SHA|SHA-224|SHA-256|SHA-384|SHA-512
# PRIV_PROTO: DES|AES|AES-192|AES-256
AUTH_MAP = {
    "MD5": config.USM_AUTH_HMAC96_MD5,
    "SHA": config.USM_AUTH_HMAC96_SHA,
    "SHA-224": config.USM_AUTH_HMAC128_SHA224,
    "SHA-256": config.USM_AUTH_HMAC192_SHA256,
    "SHA-384": config.USM_AUTH_HMAC256_SHA384,
    "SHA-512": config.USM_AUTH_HMAC384_SHA512,
}
PRIV_MAP = {
    "DES": config.USM_PRIV_CBC56_DES,
    "AES": config.USM_PRIV_CFB128_AES,
    "AES-192": config.USM_PRIV_CFB192_AES,
    "AES-256": config.USM_PRIV_CFB256_AES,
}

v3_users_raw = os.getenv("V3_USERS", "").strip()
if v3_users_raw:
    for item in v3_users_raw.split(","):
        parts = [p.strip() for p in item.split(":") if p.strip()]
        if len(parts) not in (3, 5):
            print(f"Skipping invalid V3_USERS entry: {item!r}")
            continue

        user, auth_proto, auth_pass = parts[0], parts[1].upper(), parts[2]
        auth = AUTH_MAP.get(auth_proto)
        if not auth:
            print(f"Unknown auth proto {auth_proto!r} for user {user!r}")
            continue

        if len(parts) == 3:
            # authNoPriv
            config.add_v3_user(snmpEngine, user, auth, auth_pass)
        else:
            priv_proto, priv_pass = parts[3].upper(), parts[4]
            priv = PRIV_MAP.get(priv_proto)
            if not priv:
                print(f"Unknown priv proto {priv_proto!r} for user {user!r}")
                continue
            config.add_v3_user(snmpEngine, user, auth, auth_pass, priv, priv_pass)

def on_trap(snmpEngine, stateReference, contextEngineId, contextName, varBinds, cbCtx):
    print("trap")
    peer = ("?", "?")
    # Newer API first
    try:
        tr = snmpEngine.message_dispatcher.get_transport_info(stateReference)
        peer = tr[1]
    except Exception as e_new:
        print(f"[peer] message_dispatcher.getTransportInfo failed: {type(e_new).__name__}: {e_new}")
        traceback.print_exc()
        # Fallback (older)
        try:
            tr = snmpEngine.msgAndPduDsp.getTransportInfo(stateReference)
            peer = tr[1]
        except Exception:
            pass

    print(f"\n=== TRAP from {peer[0]}:{peer[1]} ===")
    try:
        print(f"contextEngineId={contextEngineId.prettyPrint()} contextName={contextName.prettyPrint()}")
    except Exception:
        pass

    for oid, val in varBinds:
        print(f"{oid.prettyPrint()} = {val.prettyPrint()}")

ntfrcv.NotificationReceiver(snmpEngine, on_trap)

print(f"Listening for SNMP traps on {LISTEN_HOST}:{LISTEN_PORT} (UDP)")
print(f"Accepted v1/v2c communities: {', '.join(communities) if communities else '(none)'}")
print("Accepted v3 users:", ("configured via V3_USERS" if v3_users_raw else "(none)"))

snmpEngine.transport_dispatcher.job_started(1)
snmpEngine.transport_dispatcher.run_dispatcher()