FROM python:3.12-slim

# Establece el directorio de trabajo
WORKDIR /app

# Copia los requirements primero
COPY requirements.txt .

# Instala las dependencias
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copia el resto del código
COPY . .

# Comando por defecto
CMD ["python", "main.py", "AgroBot"]
