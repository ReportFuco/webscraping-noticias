"""
Tests del armado del envío por WhatsApp. Sin red y sin base: objetos falsos.

Lo que cubren es la razón de existir del corte en partes: WhatsApp trunca un
mensaje en 4.096 caracteres y con el tope de 20 noticias el envío pesa ~8.200.
Si esto se rompe, el usuario recibe la lista cortada por la mitad sin que nada
falle de forma visible.
"""
from datetime import date
from types import SimpleNamespace

import pytest

from services.news_delivery import construir_mensajes


def usuario(nombre="Gonzalo"):
    return SimpleNamespace(nombre=nombre, whatsapp="56900000000", id=1)


def noticia(n=1, excerpt="Una bajada cualquiera de la nota.", titulo=None):
    return SimpleNamespace(
        id=n,
        title=titulo or f"Titular numero {n}",
        url=f"https://medio.cl/nota-{n}",
        source="medio",
        date_preview=date(2026, 9, 7),
        excerpt=excerpt,
    )


def test_sin_noticias_no_arma_ningun_mensaje():
    assert construir_mensajes(usuario(), []) == []


def test_pocas_noticias_van_en_un_solo_mensaje():
    mensajes = construir_mensajes(usuario(), [noticia(1), noticia(2)], max_chars=3500)
    assert len(mensajes) == 1
    texto, incluidas = mensajes[0]
    assert texto.startswith("Hola Gonzalo,")
    assert len(incluidas) == 2
    # Una sola parte no lleva contador.
    assert "(1/1)" not in texto


def test_parte_cuando_no_cabe():
    noticias = [noticia(i) for i in range(1, 21)]
    mensajes = construir_mensajes(usuario(), noticias, max_chars=800)
    assert len(mensajes) > 1
    for texto, _ in mensajes:
        assert len(texto) <= 4096


def test_ninguna_noticia_se_pierde_ni_se_repite():
    noticias = [noticia(i) for i in range(1, 21)]
    mensajes = construir_mensajes(usuario(), noticias, max_chars=700)
    entregadas = [n for _, incluidas in mensajes for n in incluidas]
    assert [n.id for n in entregadas] == list(range(1, 21))


def test_la_numeracion_es_continua_entre_partes():
    noticias = [noticia(i) for i in range(1, 21)]
    mensajes = construir_mensajes(usuario(), noticias, max_chars=700)
    # La segunda parte no vuelve a empezar en 1.
    primera_linea = mensajes[1][0].split("\n")[0]
    assert not primera_linea.startswith("1. ")
    assert "20. Titular numero 20" in mensajes[-1][0]


def test_cada_parte_se_identifica_cuando_hay_varias():
    noticias = [noticia(i) for i in range(1, 21)]
    mensajes = construir_mensajes(usuario(), noticias, max_chars=700)
    total = len(mensajes)
    for numero, (texto, _) in enumerate(mensajes, start=1):
        assert f"({numero}/{total})" in texto


def test_solo_la_primera_parte_saluda():
    noticias = [noticia(i) for i in range(1, 21)]
    mensajes = construir_mensajes(usuario(), noticias, max_chars=700)
    assert mensajes[0][0].startswith("Hola Gonzalo,")
    for texto, _ in mensajes[1:]:
        assert "Hola Gonzalo," not in texto


def test_una_noticia_gigante_no_se_traga_a_las_demas():
    # Aunque un bloque solo ya pase el tope, tiene que salir en su propia parte
    # y no arrastrar a la siguiente ni quedar descartado.
    noticias = [noticia(1, excerpt="x" * 900), noticia(2)]
    mensajes = construir_mensajes(usuario(), noticias, max_chars=300)
    entregadas = [n.id for _, incluidas in mensajes for n in incluidas]
    assert entregadas == [1, 2]


def test_una_noticia_sin_bajada_no_deja_el_guion_colgando():
    mensajes = construir_mensajes(usuario(), [noticia(1, excerpt=None)])
    assert " — " not in mensajes[0][0]
