#!/usr/bin/env python3
"""
Portfolio Optimization API REST
Endpoint: POST /optimize-portfolio
Formato: multipart/form-data

Parámetros:
- file: archivo CSV con retornos diarios
- risk_level: nivel máximo de riesgo (0.01 - 2.0)
- max_weight: peso máximo por activo (0.01 - 1.0)

Respuesta: {"optimal_portfolio": {"ticker": weight, ...}}
"""

from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse
import pandas as pd
import numpy as np
from pypfopt import EfficientFrontier
import io
import warnings
from typing import Dict
import uvicorn

# Suprimir warnings
warnings.filterwarnings('ignore')

# Crear instancia de FastAPI
app = FastAPI(
    title="Portfolio Optimization API",
    description="API REST para optimización de portafolios usando modelo de Markowitz",
    version="1.0.0"
)


class PortfolioOptimizer:
    """Clase para optimización de portafolios"""
    
    @staticmethod
    def validate_csv_format(df: pd.DataFrame) -> None:
        """Valida el formato del archivo CSV"""
        
        # Verificar que no esté vacío
        if df.empty:
            raise ValueError("El archivo CSV está vacío")
        
        # Verificar dimensiones mínimas
        if df.shape[0] < 30:
            raise ValueError(f"Insuficientes datos históricos. Se requieren al menos 30 observaciones, se encontraron {df.shape[0]}")
        
        if df.shape[1] < 2:
            raise ValueError(f"Insuficientes activos. Se requieren al menos 2 activos, se encontraron {df.shape[1]}")
        
        # Verificar que los datos sean numéricos
        non_numeric_cols = []
        for col in df.columns:
            if not pd.api.types.is_numeric_dtype(df[col]):
                try:
                    pd.to_numeric(df[col], errors='raise')
                except:
                    non_numeric_cols.append(col)
        
        if non_numeric_cols:
            raise ValueError(f"Las siguientes columnas no son numéricas: {non_numeric_cols}")
        
        # Verificar rangos de retornos (deben ser retornos, no precios)
        max_val = df.max().max()
        min_val = df.min().min()
        
        if max_val > 1.0 or min_val < -1.0:
            if max_val > 100:  # Probablemente son precios
                raise ValueError("El archivo parece contener precios en lugar de retornos. Se esperan retornos diarios (valores entre -1 y 1)")
            else:
                # Valores extremos pero posibles
                print(f"⚠️  Advertencia: Se encontraron retornos extremos (min: {min_val:.4f}, max: {max_val:.4f})")
    
    @staticmethod
    def clean_data(df: pd.DataFrame) -> pd.DataFrame:
        """Limpia y procesa los datos"""
        
        original_shape = df.shape
        
        # Eliminar duplicados
        df = df.drop_duplicates()
        df = df[~df.index.duplicated(keep='first')]
        
        # Convertir todo a numérico
        for col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Manejar valores problemáticos
        df = df.replace([np.inf, -np.inf], np.nan)
        
        # Verificar porcentaje de NaN por columna
        nan_percentage = df.isna().sum() / len(df)
        problematic_cols = nan_percentage[nan_percentage > 0.1].index.tolist()
        
        if problematic_cols:
            print(f"⚠️  Eliminando columnas con >10% NaN: {problematic_cols}")
            df = df.drop(columns=problematic_cols)
        
        # Eliminar filas con NaN
        df = df.dropna()
        
        print(f"Datos procesados: {original_shape} → {df.shape}")
        
        # Verificar que aún tenemos suficientes datos
        if df.shape[0] < 30:
            raise ValueError(f"Después de la limpieza quedan insuficientes datos: {df.shape[0]} < 30")
        
        if df.shape[1] < 2:
            raise ValueError(f"Después de la limpieza quedan insuficientes activos: {df.shape[1]} < 2")
        
        return df
    
    @staticmethod
    def optimize_portfolio(df: pd.DataFrame, risk_level: float, max_weight: float) -> Dict:
        """Optimiza el portafolio usando Markowitz"""
        
        TRADING_DAYS = 252
        
        # Calcular estadísticas
        mu = df.mean() * TRADING_DAYS  # Retornos esperados anualizados
        S = df.cov() * TRADING_DAYS    # Matriz de covarianza anualizada
        
        # Verificar validez de los cálculos
        if mu.isna().any():
            raise ValueError("Error en el cálculo de retornos esperados")
        
        if S.isna().any().any():
            raise ValueError("Error en el cálculo de la matriz de covarianza")
        
        # Verificar que la matriz de covarianza es semidefinida positiva
        eigenvalues = np.linalg.eigvals(S)
        if np.any(eigenvalues <= 0):
            raise ValueError("La matriz de covarianza no es semidefinida positiva. Los datos pueden tener problemas de multicolinealidad")
        
        try:
            # Crear optimizador
            ef = EfficientFrontier(mu, S, weight_bounds=(0, max_weight))
            
            # Optimizar para máximo Sharpe ratio
            weights = ef.max_sharpe()
            cleaned_weights = ef.clean_weights()
            
            # Calcular métricas del portafolio
            expected_return, expected_volatility, sharpe_ratio = ef.portfolio_performance()
            
            # Verificar restricción de riesgo
            if expected_volatility > risk_level:
                print(f"⚠️  Volatilidad ({expected_volatility:.4f}) excede risk_level ({risk_level:.4f})")
                
                # Intentar optimizar con restricción de riesgo
                try:
                    ef_risk = EfficientFrontier(mu, S, weight_bounds=(0, max_weight))
                    ef_risk.efficient_risk(risk_level)
                    cleaned_weights = ef_risk.clean_weights()
                    expected_return, expected_volatility, sharpe_ratio = ef_risk.portfolio_performance()
                    print("✅ Aplicada restricción de riesgo")
                except Exception as e:
                    print(f"⚠️  No se pudo aplicar restricción de riesgo: {e}")
                    print("Usando portafolio de máximo Sharpe")
            
            # Preparar resultado
            result = {
                "optimal_portfolio": cleaned_weights,
                "portfolio_metrics": {
                    "expected_return": round(float(expected_return), 6),
                    "expected_volatility": round(float(expected_volatility), 6),
                    "sharpe_ratio": round(float(sharpe_ratio), 6),
                    "active_positions": sum(1 for w in cleaned_weights.values() if w > 0.001),
                    "total_weight": round(sum(cleaned_weights.values()), 6)
                }
            }
            
            return result
            
        except Exception as e:
            raise ValueError(f"Error en la optimización: {str(e)}")


@app.get("/")
async def root():
    """Endpoint de información básica"""
    return {
        "message": "Portfolio Optimization API",
        "version": "1.0.0",
        "endpoint": "POST /optimize-portfolio",
        "format": "multipart/form-data",
        "parameters": {
            "file": "CSV file with daily returns",
            "risk_level": "Maximum risk level (0.01 - 2.0)",
            "max_weight": "Maximum weight per asset (0.01 - 1.0)"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.post("/optimize-portfolio")
async def optimize_portfolio_endpoint(
    file: UploadFile = File(..., description="CSV file with daily returns"),
    risk_level: float = Form(..., description="Maximum risk level (0.01 - 2.0)"),
    max_weight: float = Form(..., description="Maximum weight per asset (0.01 - 1.0)")
):
    """
    Optimiza un portafolio a partir de retornos diarios.
    
    Returns:
        JSON: {"optimal_portfolio": {"ticker": weight, ...}}
    """
    
    try:
        # 1. Validar parámetros de entrada
        if not (0.01 <= risk_level <= 2.0):
            raise HTTPException(
                status_code=422,
                detail=f"risk_level debe estar entre 0.01 y 2.0, recibido: {risk_level}"
            )
        
        if not (0.01 <= max_weight <= 1.0):
            raise HTTPException(
                status_code=422,
                detail=f"max_weight debe estar entre 0.01 y 1.0, recibido: {max_weight}"
            )
        
        # 2. Validar archivo
        if not file.filename.lower().endswith('.csv'):
            raise HTTPException(
                status_code=422,
                detail="El archivo debe ser un CSV"
            )
        
        # 3. Leer archivo CSV
        try:
            contents = await file.read()
            df = pd.read_csv(io.StringIO(contents.decode('utf-8')), index_col=0, parse_dates=True)
        except UnicodeDecodeError:
            raise HTTPException(
                status_code=422,
                detail="Error de codificación del archivo. Asegúrate de que sea UTF-8"
            )
        except Exception as e:
            raise HTTPException(
                status_code=422,
                detail=f"Error al leer el archivo CSV: {str(e)}"
            )
        
        # 4. Validar formato del CSV
        try:
            PortfolioOptimizer.validate_csv_format(df)
        except ValueError as e:
            raise HTTPException(
                status_code=422,
                detail=f"Formato de CSV inválido: {str(e)}"
            )
        
        # 5. Limpiar datos
        try:
            df_clean = PortfolioOptimizer.clean_data(df)
        except ValueError as e:
            raise HTTPException(
                status_code=422,
                detail=f"Error en la limpieza de datos: {str(e)}"
            )
        
        # 6. Optimizar portafolio
        try:
            result = PortfolioOptimizer.optimize_portfolio(df_clean, risk_level, max_weight)
        except ValueError as e:
            raise HTTPException(
                status_code=422,
                detail=f"Error en la optimización: {str(e)}"
            )
        
        # 7. Devolver solo el formato requerido
        return {"optimal_portfolio": result["optimal_portfolio"]}
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Catch any other unexpected errors
        raise HTTPException(
            status_code=500,
            detail=f"Error interno del servidor: {str(e)}"
        )


@app.post("/optimize-portfolio-detailed")
async def optimize_portfolio_detailed_endpoint(
    file: UploadFile = File(...),
    risk_level: float = Form(...),
    max_weight: float = Form(...)
):
    """
    Endpoint alternativo que devuelve información detallada del portafolio.
    """
    
    # Reutilizar la lógica del endpoint principal
    try:
        result = await optimize_portfolio_endpoint(file, risk_level, max_weight)
        
        # Agregar métricas detalladas
        # (Re-procesar para obtener métricas adicionales)
        contents = await file.read()
        df = pd.read_csv(io.StringIO(contents.decode('utf-8')), index_col=0, parse_dates=True)
        df_clean = PortfolioOptimizer.clean_data(df)
        detailed_result = PortfolioOptimizer.optimize_portfolio(df_clean, risk_level, max_weight)
        
        return detailed_result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error interno: {str(e)}"
        )


# Configuración para ejecutar la aplicación
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )


# Ejemplo de uso con curl (para documentación)
"""
Ejemplo de uso:

curl -X POST http://localhost:8000/optimize-portfolio \
  -H "Content-Type: multipart/form-data" \
  -F "file=@returns.csv" \
  -F "risk_level=1.0" \
  -F "max_weight=0.15"

Respuesta esperada:
{
  "optimal_portfolio": {
    "SPY US Equity": 0.1234,
    "FTEC US Equity": 0.0987,
    "QQQM US Equity": 0.1500,
    ...
  }
}
"""