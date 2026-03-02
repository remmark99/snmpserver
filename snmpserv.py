import asyncio
from pysnmp.entity import engine, config
from pysnmp.carrier.asyncio.dgram import udp
from pysnmp.entity.rfc3413 import ntfrcv

ENGINE_HEX = "80001F880382B668448AF6"  # engineID устройства БЕЗ "0x"
USER = "test"
AUTH_PASS = "qwe12345"
PRIV_PASS = "qwe12345"  # если без шифрования — см. ниже

snmpEngine = engine.SnmpEngine()

# UDP/162 listener
config.add_transport(
    snmpEngine,
    udp.DOMAIN_NAME,
    udp.UdpTransport().open_server_mode(("0.0.0.0", 162))
)

# SNMPv3 user (привязка к engineID устройства)
config.add_v3_user(
    snmpEngine,
    USER,
    config.USM_AUTH_HMAC96_SHA,
    AUTH_PASS,
    config.USM_PRIV_CFB128_AES,
    PRIV_PASS,
    securityEngineId=bytes.fromhex(ENGINE_HEX),
)

def on_trap(snmpEngine, stateReference, contextEngineId, contextName, varBinds, cbCtx):
    print("trap")
    # Попробуем достать адрес отправителя
    try:
        tr = snmpEngine.msgAndPduDsp.getTransportInfo(stateReference)  # может отличаться по версиям
        peer = tr[1]  # (ip, port)
    except Exception:
        peer = ("?", "?")

    print(f"\n=== TRAP from {peer[0]}:{peer[1]} ===")
    for oid, val in varBinds:
        print(f"{oid.prettyPrint()} = {val.prettyPrint()}")

ntfrcv.NotificationReceiver(snmpEngine, on_trap)

# Запуск dispatcher (asyncio)
snmpEngine.transport_dispatcher.job_started(1)
snmpEngine.transport_dispatcher.run_dispatcher()
