// cluster_check.cpp v1.1
// Patch notes:
// - v1.1: Standalone FastJet smoke checker for Luke local realistic pp hadron ASCII outputs.
// - Compile manually if needed with: c++ cluster_check.cpp -o cluster_check $(fastjet-config --cxxflags --libs)
#include <fastjet/ClusterSequence.hh>

#include <algorithm>
#include <cmath>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

int main(int argc, char **argv) {
  if (argc < 2) {
    std::cerr << "usage: cluster_check hadrons.dat\n";
    return 2;
  }

  std::ifstream in(argv[1]);
  if (!in) {
    std::cerr << "failed_to_open " << argv[1] << "\n";
    return 2;
  }

  std::vector<fastjet::PseudoJet> particles;
  std::string line;
  while (std::getline(in, line)) {
    if (line.empty() || line[0] == '#') {
      continue;
    }
    int event = 0;
    int pid = 0;
    int status = 0;
    double e = 0.0;
    double px = 0.0;
    double py = 0.0;
    double pz = 0.0;
    std::istringstream row(line);
    if (!(row >> event >> pid >> status >> e >> px >> py >> pz)) {
      continue;
    }
    if (!std::isfinite(e) || !std::isfinite(px) || !std::isfinite(py) ||
        !std::isfinite(pz) || e <= 0.0) {
      continue;
    }
    particles.emplace_back(px, py, pz, e);
  }

  fastjet::JetDefinition jet_def(fastjet::antikt_algorithm, 0.4);
  fastjet::ClusterSequence sequence(particles, jet_def);
  auto jets = fastjet::sorted_by_pt(sequence.inclusive_jets(1.0));

  std::cout << "particles " << particles.size() << "\n";
  std::cout << "jets_pt_gt_1 " << jets.size() << "\n";
  for (size_t i = 0; i < std::min<size_t>(jets.size(), 10); ++i) {
    std::cout << "jet" << (i + 1) << "_pt " << jets[i].pt()
              << " eta " << jets[i].eta() << " phi " << jets[i].phi()
              << "\n";
  }
  return 0;
}
