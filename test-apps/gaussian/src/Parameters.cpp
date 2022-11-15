/*
 * Parameters.cpp
 *
 *  Created on: Feb 1, 2020
 *      Author: fernando
 */

#include <cuda_runtime_api.h>

#include "Parameters.h"
#include "cuda_utils.h"
#include "utils.h"
/**
 * 	if (argc < 2) {
		printf("Usage: gaussian -f filename / -s size [-q]\n\n");
		printf(
				"-q (quiet) suppresses printing the matrix and result values.\n");
		printf("-f (filename) path of input file\n");
		printf(
				"-s (size) size of matrix. Create matrix and rhs in this program \n");
		printf(
				"The first line of the file contains the dimension of the matrix, n.");
		printf("The second line of the file is a newline.\n");
		printf(
				"The next n lines contain n tab separated values for the matrix.");
		printf("The next line of the file is a newline.\n");
		printf(
				"The next line of the file is a 1xn vector with tab separated values.\n");
		printf("The next line of the file is a newline. (optional)\n");
		printf(
				"The final line of the file is the pre-computed solution. (optional)\n");
		printf("Example: matrix4.txt:\n");
		printf("4\n");
		printf("\n");
		printf("-0.6	-0.5	0.7	0.3\n");
		printf("-0.3	-0.9	0.3	0.7\n");
		printf("-0.4	-0.5	-0.3	-0.8\n");
		printf("0.0	-0.1	0.2	0.9\n");
		printf("\n");
		printf("-0.85	-0.68	0.24	-0.53\n");
		printf("\n");
		printf("0.7	0.0	-0.4	-0.5\n");
		exit(0);
	}
 *
 */
Parameters::Parameters(int argc, char* argv[]) {
	this->iterations = rad::find_int_arg(argc, argv, "--iterations", 10);
	this->verbose = rad::find_arg(argc, argv, "--verbose");
	this->debug = rad::find_arg(argc, argv, "--debug");
	this->generate = rad::find_arg(argc, argv, "--generate");
	this->input = rad::find_char_arg(argc, argv, "--input", "./input.data");
	this->gold = rad::find_char_arg(argc, argv, "--gold", "./gold.data");
	this->size = rad::find_int_arg(argc, argv, "--size", 1024);

	auto dev_prop = rad::get_device();
	this->device = dev_prop.name;
	if (this->generate) {
		this->iterations = 1;
	}

	//if it is ADD, MUL, or MAD use maximum allocation
	this->sm_count = dev_prop.multiProcessorCount;

	if (argc < 2) {
		throw_line(
				"Usage: ./cudaLUD --size N [--generate] [--input <path>] [--gold <path>] [--iterations N] [--verbose]");
	}

}

std::ostream& operator<<(std::ostream& os, const Parameters& p) {
	os << std::boolalpha;
	os << "Testing Gaussian on " << p.device << std::endl;
	os << "Matrix size: " << p.size << "x" << p.size << std::endl;
	os << "Input path: " << p.input << std::endl;
	os << "Gold path: " << p.gold << std::endl;
	os << "Iterations: " << p.iterations << std::endl;
	os << "Generate: " << p.generate << std::endl;
	os << "SM count = " << p.sm_count << std::endl;
	os << "Verbose: " << p.verbose;
	return os;
}

