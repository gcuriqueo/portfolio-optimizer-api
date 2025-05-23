# Portfolio Optimization API

API REST para optimización de portafolios usando modelo de Markowitz con maximización del Ratio de Sharpe.

## 📋 Especificaciones

- **Endpoint**: `POST /optimize-portfolio`
- **Formato**: `multipart/form-data`
- **Respuesta**: `{"optimal_portfolio": {"ticker": weight, ...}}`

## 📊 Metodología

### Métrica de Riesgo: **Volatilidad**
Estándar de la industria, eficiencia computacional, interpretabilidad directa.

### Criterio de Optimalidad: **Ratio de Sharpe**
Maximiza retorno por unidad de riesgo, balance óptimo riesgo-rendimiento.

### Modelo: **Markowitz (Teoría Moderna de Portafolios)**
Fundamento teórico sólido, optimización convexa cuadrática, manejo natural de restricciones.

## 📏 Parámetros

### `risk_level` - Volatilidad anualizada máxima
- **0.05-0.15**: Conservador a moderado
- **0.15-0.30**: Moderado a agresivo  
- **0.30-0.50**: Agresivo
- **0.50-1.00**: Muy agresivo
- **Rango API**: 0.01-2.0

### `max_weight` - Peso máximo por activo
- **0.05-0.15**: Máxima diversificación
- **0.15-0.25**: Diversificación moderada
- **0.25-0.50**: Permite concentración
- **Rango API**: 0.01-1.0

## 🚀 Deployment

```bash
# Clonar repositorio
git clone https://github.com/gcuriqueo/portfolio-optimizer-api
cd portfolio-optimizer-api

# Ejecutar con Docker Compose
docker-compose up -d

# API disponible en: http://localhost:8000
```

### Docker Compose
El archivo `docker-compose.yml` configura automáticamente:
- Puerto 8000 expuesto
- Health checks
- Restart automático

## 🔍 Ejemplo de Uso

```bash
curl -X POST http://localhost:8000/optimize-portfolio \
  -F "file=@returns.csv" \
  -F "risk_level=0.15" \
  -F "max_weight=0.20"
```

**Respuesta:**
```json
{
  "optimal_portfolio": {
    "SPY US Equity": 0.1834,
    "FTEC US Equity": 0.2000,
    "QQQM US Equity": 0.2000,
    "VUG US Equity": 0.1345,
    "SOXX US Equity": 0.1200,
    "IAUM US Equity": 0.0878,
    "XLY US Equity": 0.0743,
    "BIL US Equity": 0.0000
  }
}
```

## 📋 Formato CSV

```csv
Date,SPY US Equity,FTEC US Equity,QQQM US Equity
2023-01-01,0.001234,-0.002156,0.003421
2023-01-02,-0.000987,0.004532,-0.001234
```

**Requisitos:**
- Primera columna: fechas (YYYY-MM-DD)
- Otras columnas: retornos diarios (no precios)
- Mínimo: 30 observaciones, 2 activos
- Valores entre -1 y 1, codificación UTF-8

## 🔧 Endpoints

- `GET /` - Información básica
- `GET /health` - Health check
- `POST /optimize-portfolio` - Optimización principal

## ⚠️ Validaciones

**Códigos de respuesta:**
- 200: Optimización exitosa
- 422: Parámetros o CSV inválidos
- 500: Error interno

**Limpieza automática:** NaN, duplicados, valores extremos

## 📈 Desarrollo Local

```bash
# Instalar dependencias
pip install -r requirements.txt

# Ejecutar API
python main.py

# Modo desarrollo
uvicorn main:app --reload
```

## 🏗️ **Arquitectura Simple y Escalable para Producción**

### **📋 Componentes Principales**

Internet → API Gateway → Serverless Container → Storage

#### **1. Entrada y Seguridad**
- **API Gateway** (AWS API Gateway / GCP Apigee / Azure API Management)
- **Rate limiting** y autenticación
- **Load balancing** automático

#### **2. Compute Serverless**
- **Serverless Containers**: AWS Fargate / GCP Cloud Run / Azure Container Instances
- Auto-scaling (0 → N instancias)
- Pay-per-request

#### **3. Storage**
- **Object Storage**: AWS S3 / GCP Cloud Storage / Azure Blob Storage

### **🛠️ Tecnologías**

```yaml
Containers: Docker
Compute: Serverless containers (cualquier cloud)
Gateway: Managed API Gateway
Storage: Object storage 
CI/CD: GitHub Actions
Monitoring: Cloud-native tools