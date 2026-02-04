import requests
import sys
import json
import io
from datetime import datetime
from pathlib import Path

class VoiceFormAPITester:
    def __init__(self, base_url="https://voice-form-interface.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def log_test(self, name, success, details=""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
        
        result = {
            "test": name,
            "success": success,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{status} - {name}")
        if details:
            print(f"   Details: {details}")

    def test_api_root(self):
        """Test API root endpoint"""
        try:
            response = requests.get(f"{self.api_url}/", timeout=10)
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            if success:
                data = response.json()
                details += f", Response: {data}"
            self.log_test("API Root Endpoint", success, details)
            return success
        except Exception as e:
            self.log_test("API Root Endpoint", False, f"Error: {str(e)}")
            return False

    def test_file_upload_pdf(self):
        """Test PDF file upload"""
        try:
            # Create a simple text file to simulate PDF upload
            # The backend will handle the actual PDF processing
            test_content = "This is a test form content for PDF processing"
            
            files = {
                'file': ('test_form.pdf', test_content, 'application/pdf')
            }
            
            response = requests.post(f"{self.api_url}/upload-form", files=files, timeout=15)
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            
            if success:
                data = response.json()
                details += f", Filename: {data.get('filename')}, Success: {data.get('success')}"
            else:
                details += f", Error: {response.text}"
                
            self.log_test("PDF File Upload", success, details)
            return success
        except Exception as e:
            self.log_test("PDF File Upload", False, f"Error: {str(e)}")
            return False

    def test_file_upload_image(self):
        """Test image file upload"""
        try:
            # Create a simple text content for image simulation
            # The backend will handle the actual image processing
            test_content = "Test image content"
            
            files = {
                'file': ('test_image.png', test_content, 'image/png')
            }
            
            response = requests.post(f"{self.api_url}/upload-form", files=files, timeout=15)
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            
            if success:
                data = response.json()
                details += f", Filename: {data.get('filename')}, Success: {data.get('success')}"
            else:
                details += f", Error: {response.text}"
                
            self.log_test("Image File Upload", success, details)
            return success
        except Exception as e:
            self.log_test("Image File Upload", False, f"Error: {str(e)}")
            return False

    def test_save_submission(self):
        """Test saving form submission"""
        try:
            submission_data = {
                "form_link": "https://example.com/test-form",
                "file_name": "test_document.pdf",
                "transcription": "This is a test transcription from voice input",
                "extracted_text": "Sample extracted text from uploaded form"
            }
            
            response = requests.post(
                f"{self.api_url}/save-submission",
                json=submission_data,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            
            if success:
                data = response.json()
                details += f", ID: {data.get('id')}, Timestamp: {data.get('timestamp')}"
                # Store the ID for later tests
                self.test_submission_id = data.get('id')
            else:
                details += f", Error: {response.text}"
                
            self.log_test("Save Submission", success, details)
            return success, response.json() if success else {}
        except Exception as e:
            self.log_test("Save Submission", False, f"Error: {str(e)}")
            return False, {}

    def test_get_submissions(self):
        """Test retrieving all submissions"""
        try:
            response = requests.get(f"{self.api_url}/submissions", timeout=10)
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            
            if success:
                data = response.json()
                details += f", Count: {len(data)} submissions"
                if len(data) > 0:
                    details += f", Latest: {data[0].get('timestamp', 'N/A')}"
            else:
                details += f", Error: {response.text}"
                
            self.log_test("Get Submissions", success, details)
            return success, response.json() if success else []
        except Exception as e:
            self.log_test("Get Submissions", False, f"Error: {str(e)}")
            return False, []

    def test_delete_submission(self, submission_id):
        """Test deleting a specific submission"""
        try:
            response = requests.delete(f"{self.api_url}/submissions/{submission_id}", timeout=10)
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            
            if success:
                data = response.json()
                details += f", Success: {data.get('success')}, Message: {data.get('message')}"
            else:
                details += f", Error: {response.text}"
                
            self.log_test("Delete Submission", success, details)
            return success
        except Exception as e:
            self.log_test("Delete Submission", False, f"Error: {str(e)}")
            return False

    def test_invalid_file_upload(self):
        """Test uploading invalid file format"""
        try:
            files = {
                'file': ('test.txt', 'This is a text file', 'text/plain')
            }
            
            response = requests.post(f"{self.api_url}/upload-form", files=files, timeout=10)
            # Should return 400 for unsupported format
            success = response.status_code == 400
            details = f"Status: {response.status_code} (Expected 400 for invalid format)"
            
            self.log_test("Invalid File Upload", success, details)
            return success
        except Exception as e:
            self.log_test("Invalid File Upload", False, f"Error: {str(e)}")
            return False

    def test_delete_nonexistent_submission(self):
        """Test deleting non-existent submission"""
        try:
            fake_id = "nonexistent-id-12345"
            response = requests.delete(f"{self.api_url}/submissions/{fake_id}", timeout=10)
            # Should return 404 for non-existent submission
            success = response.status_code == 404
            details = f"Status: {response.status_code} (Expected 404 for non-existent ID)"
            
            self.log_test("Delete Non-existent Submission", success, details)
            return success
        except Exception as e:
            self.log_test("Delete Non-existent Submission", False, f"Error: {str(e)}")
            return False

    def run_all_tests(self):
        """Run all API tests"""
        print(f"🚀 Starting Voice Form API Tests")
        print(f"📍 Testing API at: {self.api_url}")
        print("=" * 60)
        
        # Test basic connectivity
        if not self.test_api_root():
            print("❌ API root endpoint failed - stopping tests")
            return False
        
        # Test file upload endpoints
        self.test_file_upload_pdf()
        self.test_file_upload_image()
        self.test_invalid_file_upload()
        
        # Test submission workflow
        success, submission_data = self.test_save_submission()
        if success and submission_data.get('id'):
            submission_id = submission_data['id']
            
            # Test getting submissions
            self.test_get_submissions()
            
            # Test deleting the submission we created
            self.test_delete_submission(submission_id)
        
        # Test error cases
        self.test_delete_nonexistent_submission()
        
        # Print summary
        print("=" * 60)
        print(f"📊 Test Summary:")
        print(f"   Total Tests: {self.tests_run}")
        print(f"   Passed: {self.tests_passed}")
        print(f"   Failed: {self.tests_run - self.tests_passed}")
        print(f"   Success Rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
        
        return self.tests_passed == self.tests_run

def main():
    tester = VoiceFormAPITester()
    success = tester.run_all_tests()
    
    # Save test results
    results_file = Path("/app/test_reports/backend_api_results.json")
    results_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(results_file, 'w') as f:
        json.dump({
            "summary": {
                "total_tests": tester.tests_run,
                "passed_tests": tester.tests_passed,
                "failed_tests": tester.tests_run - tester.tests_passed,
                "success_rate": (tester.tests_passed/tester.tests_run)*100 if tester.tests_run > 0 else 0,
                "timestamp": datetime.now().isoformat()
            },
            "test_results": tester.test_results
        }, f, indent=2)
    
    print(f"\n📄 Detailed results saved to: {results_file}")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())