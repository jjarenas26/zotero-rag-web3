from pipelines.academic_ingestion_pipeline import AcademicIngestionPipeline

pipeline = AcademicIngestionPipeline()

pipeline.ingest_collection("data/raw")
