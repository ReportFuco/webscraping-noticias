from io import BytesIO
import base64
import requests


class EvolutionWhatsApp:
    """
    Esta clase te ayuda a utilizar Evolution api a través de Python de manera sencilla, 
    permitiendo enviar mensajes y fotos.
    si no tienes creada una instancia de Evolution API, debes dirigirte al siguiente aca: 
    
    [Docummentación de Evolution API](https://doc.evolution-api.com/v1/en/get-started/introduction)
    """

    def __init__(
            self,
            url:str,
            instance:str,
            api_key:str
        ):
        
        self.url = url
        self.instance = instance
        self.api_key = api_key

    @property        
    def _headers(self):
        return {
            "apikey": self.api_key,
            "Content-Type": "application/json"
        }

    def enviar_mensaje(
            self, 
            numero:str, 
            mensaje:str,
            delay:int = 1000
        )->bool:
        """
        Envía un mensaje de texto a un número específico usando Evolution API.

        Args:
            numero (int): Número de teléfono en formato internacional (ej: 569...).
            mensaje (str): Texto que deseas enviar.

        Returns:
            None
        """

        try:
            res = requests.post(
                    f"{self.url}/message/sendText/{self.instance}",
                    headers=self._headers,
                    json={
                        "number": numero,
                        "text": mensaje,
                        "delay":delay
                    }
                )
            if res.status_code == 201:
                print("mensaje enviado")
                print(res.content)
                return True
            else:
                print(res.status_code)
                print(res.content)
                print(res.url)
        except requests.RequestException as e:
            print(f"El mensaje no fue enviado: {e}")
            return False

    def enviar_mensaje_con_boton(
            self,
            numero:int,
            titulo:str,
            descripcion:str,
            footer:str,
            botones:list,
        )->bool:
        """
        Envía un mensaje de texto con botones personalizables a un número específico usando Evolution API.
        >>> Nota: Debes tener WhatsApp Bussines para poder enviar este mensaje.

        Args:
            numero (int): Número de teléfono en formato internacional (ej: 569...).
            titulo (str): Título del mensaje que quieres enviar.
            descripcion (str): cuerpo del mensaje que quieres enviar.
            footer (str): es el pie del mensaje que quieres enviar.
            botones (list): es una lista con los botones a utilizar dentro del mensaje.

        Returns:
            None
        """

        try:
            requests.post(
                    f"{self.url}/message/sendButtons/{self.instance}",
                    headers=self._headers,
                    json={
                        "number": str(numero),
                        "title": titulo,
                        "description": descripcion,
                        "footer": footer,
                        "buttons": botones
                    }
                )
            print("✅ Mensaje con botones enviado")
        except requests.exceptions.RequestException as e:
            print(f"❌ Error al enviar mensaje con botones: {e}")

    def enviar_mensaje_foto(
            self,
            numero:int,
            mensaje,
            path_foto:str = None,
            buffer:BytesIO = None,
            delay:int = None
        )->bool:
        """
        Envía una foto a un número específico usando Evolution API.

        Args:
            numero (int): Número de teléfono en formato internacional (ej: 569...).
            mensaje (str): Texto que deseas enviar.
            path_foto (str): Path del directorio de la foto que quieres enviar.
            buffer (BytesIO): Buffer de la foto que quieres enviar en el caso de que solo trabajes con memoria.

        Returns:
            bool: True si se envió correctamente, False en caso de error.
        """


        if path_foto and buffer:
            raise ValueError("Solo puedes proporcionar 'path_foto' o 'buffer', no ambos.")
    
        if not path_foto and not buffer:
            raise ValueError("Debes proporcionar al menos 'path_foto' o 'buffer'.")

        if buffer:
            if not isinstance(buffer, BytesIO):
                raise TypeError("'buffer' debe ser un objeto BytesIO.")
            buffer.seek(0)
            img = base64.b64encode(buffer.read()).decode("utf-8")   
            
        elif path_foto:
            
            with open(path_foto, "rb") as file:
                img = (base64.b64encode(file.read())
                    .decode("utf-8")
                )

        try:
            requests.post(
                f"{self.url}/message/sendMedia/{self.instance}",
                headers=self._headers,
                json={
                    "media": img,
                    "caption": mensaje,
                    "mediatype": "image",
                    "number": str(numero),
                    "mimetype": "image/jpeg",
                    "delay": delay
                },
            )
            print("Mensaje con imagen enviado")
            
            return True
        
        except requests.RequestException as e:
            
            print(f"El mensaje no fue enviado: {e}")
            
            return False

