# SKFunction Examples

## Machine Learning Pipeline Example

```python
from suitkaise import xprocess, sktree, skfunction

xp = xprocess.CrossProcessing()

# create a machine learning pipeline that works across processes
def preprocess_data(data_path, model_type, batch_size, normalize=True):
    # Expensive preprocessing that takes 10+ minutes
    return processed_data

def train_model(processed_data, model_type, learning_rate, epochs):
    # Training that takes hours!
    return trained_model

# create reusable presets for different trials
image_processing = skfunction.create("image_classifier", preprocess_data, {
    "model_type": "CNN",
    "batch_size": 32,
    "normalize": True
})

# use the same function base callable but with different param values!
nlp_processing = skfunction.create("text_classifier", preprocess_data, {
    "model_type": "Transformer", 
    "batch_size": 16,
    "normalize": False
})

# Register in global function library
tree = sktree.connect()
# will also autoregister to a skfunction registry, allowing you to search either actual location or func rej
tree.add("image_classifier", image_processing, path="ml/preprocessing")
tree.add("text_classifier", nlp_processing, path="ml/preprocessing")

# you can ALSO add a function straight to the function registry
# will FAIL if a tree or global storage isn't connected
tree.add_to_funcrej("image_classifier", image_processing, connection=tree)

# Now ANY process can discover and use these functions themselves
# Process 1: Data preprocessing worker
with xp.ProcessSetup() as setup:
    # get available preprocessing functions (if relpath is given, tries to normalize it first)
    available_functions = tree.get_all_from("ml/preprocessing")
    # or...
    image_classifier = tree.get_from_funcrej("image_classifier")

    # execute correct one based on job type
    if job_type == "images":
        result = available_functions["image_classifier"].call(data_path="./images/")

# Process 2: Hyperparameter tuning worker  
with xprocess.ProcessSetup() as setup:
    # Use the same preprocessing function with different parameters
    preprocessor = tree.get_from_funcrej("image_classifier")
    
    # Override specific parameters for this experiment
    result = preprocessor.call(data_path="./experiments/run_5/", batch_size=64)

# Process 3: Production inference server
@skfunction.cache_results(ttl=3600, save_to_file=True)
def inference_pipeline(image_data):
    preprocessor = tree.get_from_funcrej("image_classifier") 
    model = tree.get("trained_model_v3")
    
    # Cached preprocessing + model inference
    processed = preprocessor.call(image_data)
    return model.predict(processed)

# The power: Functions are discoverable, reusable across processes, 
# cacheable, and maintain full execution context

# NOTE: you can use tree.get instead of tree.get_from_funcrej, but it will take much longer to find the function!
```

## Business Reports Example

```python
# Let's say you run a small business and need different reports
from suitkaise import skfunction, sktree, autopath

# Step 1: Define a flexible report function
@autopath(defaultpath="./reports/misc")
def generate_sales_report(store_name, start_date, end_date, 
                         format="PDF", include_charts=True, 
                         email_to=None, save_location_path=None):
    """
    Creates a sales report - normally takes 2-3 minutes to run
    """
    # Imagine this does: fetch data, calculate totals, create charts, format as PDF
    print(f"Generating {format} report for {store_name} from {start_date} to {end_date}")
    # ... complex report generation logic ...
    return f"Report saved to {save_location}"

# Step 2: Create presets for different stores (avoid repetition!)
downtown_store = skfunction.create("downtown_reports", generate_sales_report, {
    "store_name": "Downtown Branch",
    "format": "PDF",
    "include_charts": True,
    "email_to": "manager.downtown@business.com",
    "save_location": "./reports/downtown/"
})

mall_store = skfunction.create("mall_reports", generate_sales_report, {
    "store_name": "Mall Location", 
    "format": "Excel",
    "include_charts": False,  # Mall manager prefers Excel
    "email_to": "manager.mall@business.com",
    "save_location": "./reports/mall/"
})

# Step 3: Save these presets so anyone can use them
tree = sktree.connect()
tree.add("downtown_reports", downtown_store, path="business/reports")
tree.add("mall_reports", mall_store, path="business/reports")

# Now the magic happens...

# ✅ Your assistant can generate reports without knowing all the details:
downtown_report = tree.get("downtown_reports")
downtown_report.call(start_date="2024-01-01", end_date="2024-01-31")
# Automatically uses: PDF format, includes charts, emails to right person, saves to right folder

# ✅ Different computers/processes can run the same reports:
# On your laptop, your server, your assistant's computer - same exact setup (just make sure to include .sk files that have the persistent data!)

# ✅ Override settings when needed:
# Emergency report with different format
downtown_report.call(
    start_date="2024-06-01", 
    end_date="2024-06-28",
    format="Excel",  # Override just this one setting
    email_to="ceo@business.com"  # Send to CEO instead
)

# ✅ Build complex workflows easily:
def monthly_report_batch():
    """Generate all monthly reports automatically"""
    all_report_functions = tree.get_all_from("business/reports")
    
    for store_name, report_func in all_report_functions.items():
        print(f"Generating report for {store_name}...")
        report_func.call(start_date="2024-06-01", end_date="2024-06-30")
    
    print("All monthly reports completed!")

# ✅ Add caching and/or saving so you don't regenerate identical reports:
@skfunction.cache_results(save_to_file="file/to/save/to") # or just skfunction.save_results("file/to/save/to")
def saved_annual_report(store_name, year):
    # Annual reports take 20+ minutes - cache them!
    return generate_sales_report(
        store_name=store_name,
        start_date=f"{year}-01-01", 
        end_date=f"{year}-12-31",
        format="PDF"
    )
```