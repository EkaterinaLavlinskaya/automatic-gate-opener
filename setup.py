from setuptools import setup, find_packages

setup(
    name="automatic-gate",
    version="1.0.0",
    description="Automatic gate control with license plate recognition",
    author="Ekaterina Lavlinskaya",
    packages=find_packages(),
    install_requires=[
        "ultralytics",
        "easyocr",
        "opencv-python",
        "pyserial",
        "requests",
    ],
)
