#from pipelines.academic_ingestion_pipeline import AcademicIngestionPipeline
from pipelines.academic_ingestion_pipelinev2 import AcademicIngestionPipeline

pipeline = AcademicIngestionPipeline()

pipeline.ingest_collection("data/raw")
