"""
Tests de la detección de fuentes muertas. Sin red y sin base: sesión falsa.

Lo que cubren es la regla que evita el spam —avisar una sola vez, al cruzar el
umbral— y que la racha se corte apenas la fuente devuelve algo. Si esto se
rompe, o llegan doce avisos al día de lo mismo, o no llega ninguno.
"""
from types import SimpleNamespace

from services.salud_fuentes import (
    ESTADO_VACIA,
    avisar_fuentes_vacias,
    contar_racha,
    fuentes_a_avisar,
    mensaje_alerta,
    racha_vacia,
)


class SesionFalsa:
    """
    Devuelve los estados que se le configuren por fuente, respetando el
    `limit` de la consulta real.
    """

    def __init__(self, estados_por_fuente: dict[str, list[str]]):
        self.estados_por_fuente = estados_por_fuente
        self.consultas: list[str] = []

    def execute(self, statement):
        # La fuente viaja en el WHERE como parámetro vinculado.
        source = next(
            valor
            for valor in statement.compile().params.values()
            if isinstance(valor, str)
        )
        limite = statement._limit_clause.value
        self.consultas.append(source)
        estados = self.estados_por_fuente.get(source, [])[:limite]
        return SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: estados))


def test_racha_se_corta_con_el_primer_estado_bueno():
    assert contar_racha([ESTADO_VACIA, ESTADO_VACIA, "ok", ESTADO_VACIA]) == 2


def test_sin_historial_no_hay_racha():
    assert contar_racha([]) == 0


def test_una_corrida_con_error_tambien_corta_la_racha():
    # Un error es otra cosa y ya tiene su propio registro: no debe sumar acá.
    assert contar_racha([ESTADO_VACIA, "error", ESTADO_VACIA]) == 1


def test_racha_vacia_consulta_solo_hasta_el_limite():
    sesion = SesionFalsa({"elmostrador": [ESTADO_VACIA] * 10})
    assert racha_vacia(sesion, "elmostrador", limite=3) == 3


def test_avisa_solo_cuando_cruza_el_umbral():
    sesion = SesionFalsa({"elmostrador": [ESTADO_VACIA, ESTADO_VACIA, ESTADO_VACIA]})
    assert fuentes_a_avisar(sesion, ["elmostrador"], umbral=3) == ["elmostrador"]


def test_no_avisa_antes_del_umbral():
    sesion = SesionFalsa({"elmostrador": [ESTADO_VACIA, ESTADO_VACIA, "ok"]})
    assert fuentes_a_avisar(sesion, ["elmostrador"], umbral=3) == []


def test_no_vuelve_a_avisar_si_sigue_rota():
    # Cuarta corrida vacía seguida: la racha pasó el umbral y ya se avisó.
    sesion = SesionFalsa({"elmostrador": [ESTADO_VACIA] * 4})
    assert fuentes_a_avisar(sesion, ["elmostrador"], umbral=3) == []


def test_avisa_de_nuevo_si_se_recupera_y_vuelve_a_caer():
    sesion = SesionFalsa(
        {"elmostrador": [ESTADO_VACIA, ESTADO_VACIA, ESTADO_VACIA, "ok", ESTADO_VACIA]}
    )
    assert fuentes_a_avisar(sesion, ["elmostrador"], umbral=3) == ["elmostrador"]


def test_evalua_cada_fuente_por_separado():
    sesion = SesionFalsa(
        {
            "elmostrador": [ESTADO_VACIA] * 3,
            "publimetro": [ESTADO_VACIA, "ok", "ok"],
        }
    )
    avisar = fuentes_a_avisar(sesion, ["elmostrador", "publimetro"], umbral=3)
    assert avisar == ["elmostrador"]


def test_mensaje_nombra_las_fuentes_y_el_umbral():
    texto = mensaje_alerta(["retailactual", "elmostrador"], umbral=3)
    assert "3 corridas" in texto
    assert "• elmostrador" in texto
    assert "• retailactual" in texto
    # Ordenado, para que dos avisos iguales se lean iguales.
    assert texto.index("elmostrador") < texto.index("retailactual")


def test_sin_destinos_no_intenta_enviar():
    enviados = avisar_fuentes_vacias(
        ["elmostrador"],
        umbral=3,
        destinos=[],
        credenciales={"url": "x", "instance": "y", "api_key": "z"},
    )
    assert enviados == 0


def test_sin_credenciales_no_intenta_enviar():
    enviados = avisar_fuentes_vacias(
        ["elmostrador"],
        umbral=3,
        destinos=["56900000000"],
        credenciales={"url": "", "instance": "", "api_key": ""},
    )
    assert enviados == 0


def test_sin_fuentes_no_hace_nada():
    enviados = avisar_fuentes_vacias(
        [],
        umbral=3,
        destinos=["56900000000"],
        credenciales={"url": "x", "instance": "y", "api_key": "z"},
    )
    assert enviados == 0
