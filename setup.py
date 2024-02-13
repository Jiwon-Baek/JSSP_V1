"""
2023-09-13
https://www.holaxprogramming.com/2017/06/28/python-project-structures/
위 링크 보고 파이썬 프로젝트 구조 연습하는 중

PyPI 저장소 등에 배포할 때 사용하는 용도
"""
import io
from setuptools import find_packages, setup


# Read in the README for the long description on PyPI
def long_description():
    with io.open('README.rst', 'r', encoding='utf-8') as f:
        readme = f.read()
    return readme

setup(name='objects',
      version='0.1',
      description='JSSP objects',
      long_description=long_description(),
      url='https://github.com/000/000',
      author='Jiwon Baek',
      author_email='baekjiwon@snu.ac.kr',
      license='MIT',
      packages=find_packages(),
      classifiers=[
          'Programming Language :: Python :: 2.7',
          'Programming Language :: Python :: 3',
          'Programming Language :: Python :: 3.6',
          ],
      zip_safe=False)
