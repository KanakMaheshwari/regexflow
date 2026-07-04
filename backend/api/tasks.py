import os
import time
import pandas as pd


from celery import shared_task
from .models import ProcessingJob



@shared_task
def process_uploaded_file(job_id,instruction):

    job = ProcessingJob.objects.get(id=job_id)

    try:
        job.status = "RUNNING"
        job.progress = 0
        job.save()

        print(f"Started Job {job.id}")
        print(f"Instruction: {instruction}")

        # Get the uploaded file path
        file_path = job.filename.path

        # Read file
        if file_path.endswith(".csv"):
            df = pd.read_csv(file_path)

        elif file_path.endswith(".xlsx"):
            df = pd.read_excel(file_path)

        else:
            job.status = "FAILED"
            job.save()
            return False

        rows = len(df)

        
        for i in range(rows):

            time.sleep(0.02)

            progress = int(((i + 1) / rows) * 100)

           
            if progress > job.progress:
                job.progress = progress
                job.save()

        print(f"Processed {rows} rows")

      

        filename = os.path.basename(job.filename.name)

        processed_dir = os.path.join("uploads", "processed")
        os.makedirs(processed_dir, exist_ok=True)

        output_path = os.path.join(
            processed_dir,
            f"processed_{filename}"
        )

        if filename.endswith(".csv"):
            df.to_csv(output_path, index=False)

        else:
            df.to_excel(output_path, index=False)

        # Save relative path in FileField
        job.output_file.name = f"processed/processed_{filename}"

        job.status = "SUCCESS"
        job.progress = 100
        job.save()

        print("Finished!")

        return True

    except Exception as e:

        print(e)

        job.status = "FAILED"
        job.save()

        return False