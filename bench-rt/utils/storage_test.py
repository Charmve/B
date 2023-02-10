import os  # noqa: F401

from google.cloud import storage

# gcloud config set project local-index-314711
# os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = '/home/qcraft/.config/gcloud/application_default_credentials.json'


def authenticate_implicit_with_adc(project_id="local-index-314711"):
    """
    When interacting with Google Cloud Client libraries, the library can auto-detect the
    credentials to use.

    // TODO(Developer):
    //  1. Before running this sample,
    //  set up ADC as described in https://cloud.google.com/docs/authentication/external/set-up-adc
    //  2. Replace the project variable.
    //  3. Make sure that the user account or service account that you are using
    //  has the required permissions. For this sample, you must have "storage.buckets.list".
    Args:
        project_id: The project id of your Google Cloud project.
    """

    # This snippet demonstrates how to list buckets.
    # *NOTE*: Replace the client created below with the client required for your application.
    # Note that the credentials are not specified when constructing the client.
    # Hence, the client library will look for credentials using ADC.
    storage_client = storage.Client(project=project_id)
    buckets = storage_client.list_buckets()
    print("Buckets:")
    for bucket in buckets:
        print(bucket.name)
    print("Listed all storage buckets.")


def run_quickstart():
    # [START storage_quickstart]
    # Imports the Google Cloud client library

    # Instantiates a client
    storage_client = storage.Client()

    # The name for the new bucket
    bucket_name = "my-new-bucket"

    # Creates the new bucket
    bucket = storage_client.create_bucket(bucket_name)

    print(f"Bucket {bucket.name} created.")
    # [END storage_quickstart]


if __name__ == "__main__":
    authenticate_implicit_with_adc()
    # run_quickstart()
