/*******************************************************************************
 * Copyright (c) The JETSCAPE Collaboration, 2018
 *
 * Modular, task-based framework for simulating all aspects of heavy-ion
 *collisions
 *
 * For the list of contributors see AUTHORS.
 *
 * Report issues at https://github.com/JETSCAPE/JETSCAPE/issues
 *
 * or via email to bugs.jetscape@gmail.com
 *
 * Distributed under the GNU General Public License 3.0 (GPLv3 or later).
 * See COPYING for details.
 ******************************************************************************/
// Local v251 diagnostic patch note:
//   Fix y-grid metadata forwarding for in-memory MUSIC histories and replace
//   shell-based freezeout surface concatenation with checked C++ file handling.
// Local v252 medium-activation patch note:
//   For 3D-Glauber string-source pp workflows, copy completed MUSIC evolution
//   history into JETSCAPE bulk_info even when source terms exist, so MATTER
//   queries the framework hydro history instead of stale/cleared live MUSIC
//   memory. Adds local QA logs for hydro history and query range diagnostics.
//   Treat single-eta copied histories as eta-collapsed/boost-invariant for
//   JETSCAPE interpolation so MATTER queries are not all rejected by eta range.

#include <glob.h>
#include <unistd.h>
#include <stdio.h>
#include <sys/stat.h>
#include <MakeUniqueHelper.h>

#include <algorithm>
#include <cmath>
#include <fstream>
#include <string>
#include <sstream>
#include <vector>
#include <memory>
#include <regex>
#include <stdexcept>

#include "JetScapeLogger.h"
#include "MusicWrapper.h"
#include "surfaceCell.h"

using namespace Jetscape;

// Register the module with the base class
RegisterJetScapeModule<MpiMusic> MpiMusic::reg("MUSIC");

MpiMusic::MpiMusic() {
  hydro_status = NOT_START;
  freezeout_temperature = 0.0;
  doCooperFrye = 0;
  flag_output_evo_to_file = 0;
  flag_output_evo_to_memory = 0;
  flag_surface_in_memory = 0;
  has_source_terms = false;
  SetId("MUSIC");
  hydro_source_terms_ptr =
      std::shared_ptr<HydroSourceJETSCAPE>(new HydroSourceJETSCAPE());
  hydro_source_terms_ptr->set_source_tau_max(1000.0);
}

MpiMusic::~MpiMusic() {}

void MpiMusic::InitializeHydro(Parameter parameter_list) {
  JSINFO << "Initialize MUSIC ...";
  VERBOSE(8);

  string input_file = GetXMLElementText({"Hydro", "MUSIC", "MUSIC_input_file"});
  doCooperFrye =
      GetXMLElementInt({"Hydro", "MUSIC", "Perform_CooperFrye_Freezeout"});

  music_hydro_ptr = std::unique_ptr<MUSIC>(new MUSIC(input_file));

  // overwrite input options
  int echoLevel = GetXMLElementInt({"vlevel"});
  music_hydro_ptr->set_parameter("JSechoLevel", echoLevel);

  flag_output_evo_to_file =
      (GetXMLElementInt({"Hydro", "MUSIC", "output_evolution_to_file"}));
  if (flag_output_evo_to_file == 1) {
    music_hydro_ptr->set_parameter("output_evolution_data", 2);
  } else {
    music_hydro_ptr->set_parameter("output_evolution_data", 0);
  }

  flag_preEq_output_evo_to_memory =
      (GetXMLElementInt({"Preequilibrium", "evolutionInMemory"}));
  flag_output_evo_to_memory =
      (GetXMLElementInt({"Hydro", "MUSIC", "output_evolution_to_memory"}));
  if (flag_output_evo_to_memory == 1) {
    music_hydro_ptr->set_parameter("store_hydro_info_in_memory", 1);
  } else {
    music_hydro_ptr->set_parameter("store_hydro_info_in_memory", 0);
  }
  music_hydro_ptr->set_parameter(
      "output_evolution_every_N_timesteps",
      GetXMLElementInt(
          {"Hydro", "MUSIC", "output_evolution_every_N_timesteps"}));

  flag_surface_in_memory =
      GetXMLElementInt({"Hydro", "MUSIC", "surface_in_memory"});
  if (flag_surface_in_memory == 1) {
    music_hydro_ptr->set_parameter("surface_in_memory", 1);
  } else {
    music_hydro_ptr->set_parameter("surface_in_memory", 0);
  }

  int EOS = GetXMLElementInt({"Hydro", "MUSIC", "EOS"});
  music_hydro_ptr->set_parameter("EOS", EOS);
  // Try to reset the EOS in the music input file
  // This is needed for iSS, which reads this parameter from the music input
  // file
  try {
    update_music_input_parameter(input_file, "EOS_to_use", EOS);
  } catch (const std::exception &e) {
    JSWARN << "Error updating EOS_to_use in MUSIC input file: " << e.what();
  }

  int beastMode = (GetXMLElementInt({"Hydro", "MUSIC", "beastMode"}));
  music_hydro_ptr->set_parameter("beastMode", beastMode);

  double tau_hydro =
      (GetXMLElementDouble({"Hydro", "MUSIC", "Initial_time_tau_0"}));
  music_hydro_ptr->set_parameter("Initial_time_tau_0", tau_hydro);

  double eta_over_s =
      (GetXMLElementDouble({"Hydro", "MUSIC", "shear_viscosity_eta_over_s"}));
  if (eta_over_s > 1e-6) {
    music_hydro_ptr->set_parameter("Viscosity_Flag_Yes_1_No_0", 1);
    music_hydro_ptr->set_parameter("Include_Shear_Visc_Yes_1_No_0", 1);
    music_hydro_ptr->set_parameter("Shear_to_S_ratio", eta_over_s);
  } else if (eta_over_s >= 0.) {
    music_hydro_ptr->set_parameter("Viscosity_Flag_Yes_1_No_0", 0);
    music_hydro_ptr->set_parameter("Include_Shear_Visc_Yes_1_No_0", 0);
  } else {
    JSWARN << "The input shear viscosity is negative! eta/s = " << eta_over_s;
    exit(1);
  }

  initialProfile_ = (GetXMLElementInt({"Hydro", "MUSIC", "InitialProfile"}));
  music_hydro_ptr->set_parameter("Initial_profile", initialProfile_);
  double string_source_sigma_x =
      (GetXMLElementDouble({"Hydro", "MUSIC", "string_source_sigma_x"}));
  music_hydro_ptr->set_parameter("string_source_sigma_x",
                                 string_source_sigma_x);
  double string_source_sigma_eta =
      (GetXMLElementDouble({"Hydro", "MUSIC", "string_source_sigma_eta"}));
  music_hydro_ptr->set_parameter("string_source_sigma_eta",
                                 string_source_sigma_eta);
  double stringPreEqFlowFactor =
      (GetXMLElementDouble({"Hydro", "MUSIC", "stringPreEqFlowFactor"}));
  music_hydro_ptr->set_parameter("stringPreEqFlowFactor",
                                 stringPreEqFlowFactor);

  int flag_shear_Tdep =
      (GetXMLElementInt({"Hydro", "MUSIC", "T_dependent_Shear_to_S_ratio"}));
  if (flag_shear_Tdep > 0) {
    music_hydro_ptr->set_parameter("Viscosity_Flag_Yes_1_No_0", 1);
    music_hydro_ptr->set_parameter("T_dependent_Shear_to_S_ratio",
                                   flag_shear_Tdep);
    if (flag_shear_Tdep == 3) {
      double shear_kinkT = (GetXMLElementDouble(
          {"Hydro", "MUSIC", "shear_viscosity_3_T_kink_in_GeV"}));
      music_hydro_ptr->set_parameter("shear_viscosity_3_T_kink_in_GeV",
                                     shear_kinkT);
      double shear_lowTslope = (GetXMLElementDouble(
          {"Hydro", "MUSIC", "shear_viscosity_3_low_T_slope_in_GeV"}));
      music_hydro_ptr->set_parameter("shear_viscosity_3_low_T_slope_in_GeV",
                                     shear_lowTslope);
      double shear_highTslope = (GetXMLElementDouble(
          {"Hydro", "MUSIC", "shear_viscosity_3_high_T_slope_in_GeV"}));
      music_hydro_ptr->set_parameter("shear_viscosity_3_high_T_slope_in_GeV",
                                     shear_highTslope);
      double shear_kink = (GetXMLElementDouble(
          {"Hydro", "MUSIC", "shear_viscosity_3_at_kink"}));
      music_hydro_ptr->set_parameter("shear_viscosity_3_at_kink", shear_kink);
    } else if (flag_shear_Tdep == 2) {
      double shear_min =
          GetXMLElementDouble({"Hydro", "MUSIC", "shear_viscosity_2_min"});
      music_hydro_ptr->set_parameter("shear_viscosity_2_min", shear_min);
      double shear_slope =
          GetXMLElementDouble({"Hydro", "MUSIC", "shear_viscosity_2_slope"});
      music_hydro_ptr->set_parameter("shear_viscosity_2_slope", shear_slope);
      double shear_curv =
          GetXMLElementDouble({"Hydro", "MUSIC", "shear_viscosity_2_curv"});
      music_hydro_ptr->set_parameter("shear_viscosity_2_curv", shear_curv);
    }
  }
  int muB_dependent_Shear_to_S_ratio =
      GetXMLElementInt({"Hydro", "MUSIC", "muB_dependent_Shear_to_S_ratio"});
  if (muB_dependent_Shear_to_S_ratio > 0) {
    music_hydro_ptr->set_parameter("muB_dependent_Shear_to_S_ratio",
                                   muB_dependent_Shear_to_S_ratio);
    if (muB_dependent_Shear_to_S_ratio == 10) {
      double shear_muBDep_alpha =
          GetXMLElementDouble({"Hydro", "MUSIC", "shear_10_muBDep_alpha"});
      music_hydro_ptr->set_parameter("shear_10_muBDep_alpha",
                                     shear_muBDep_alpha);
      double shear_muBDep_slope =
          GetXMLElementDouble({"Hydro", "MUSIC", "shear_10_muBDep_slope"});
      music_hydro_ptr->set_parameter("shear_10_muBDep_slope",
                                     shear_muBDep_slope);
      double shear_muBDep_scale =
          GetXMLElementDouble({"Hydro", "MUSIC", "shear_10_muBDep_scale"});
      music_hydro_ptr->set_parameter("shear_10_muBDep_scale",
                                     shear_muBDep_scale);
    } else if (muB_dependent_Shear_to_S_ratio == 7) {
      double shear_muBf0p4 =
          GetXMLElementDouble({"Hydro", "MUSIC", "shear_7_muBf0p4"});
      if (shear_muBf0p4 < 0) {
        // set to 1
        shear_muBf0p4 = 1.0;
      }
      music_hydro_ptr->set_parameter("shear_7_muBf0p4", shear_muBf0p4);
      double shear_muBf0p2 =
          GetXMLElementDouble({"Hydro", "MUSIC", "shear_7_muBf0p2"});
      if (shear_muBf0p2 < 0) {
        // set to (shear_muBf0p4 + 1) / 2
        shear_muBf0p2 = (shear_muBf0p4 + 1) / 2.;
      }
      music_hydro_ptr->set_parameter("shear_7_muBf0p2", shear_muBf0p2);
    }
  }

  int flag_bulkvis = GetXMLElementInt(
      {"Hydro", "MUSIC", "temperature_dependent_bulk_viscosity"});
  if (flag_bulkvis != 0) {
    music_hydro_ptr->set_parameter("Include_Bulk_Visc_Yes_1_No_0", 1);
    // Try to reset the flag Include_Bulk_Visc_Yes_1_No_0 in the music input
    // file This is needed for iSS, which reads this parameter from the music
    // input file
    try {
      update_music_input_parameter(input_file, "Include_Bulk_Visc_Yes_1_No_0",
                                   flag_bulkvis);
    } catch (const std::exception &e) {
      JSWARN
          << "Error updating Include_Bulk_Visc_Yes_1_No_0 in MUSIC input file: "
          << e.what();
    }
    music_hydro_ptr->set_parameter("T_dependent_Bulk_to_S_ratio", flag_bulkvis);
    if (flag_bulkvis == 3) {
      double bulk_max =
          GetXMLElementDouble({"Hydro", "MUSIC", "bulk_viscosity_3_max"});
      music_hydro_ptr->set_parameter("bulk_viscosity_3_max", bulk_max);
      double bulk_peakT = GetXMLElementDouble(
          {"Hydro", "MUSIC", "bulk_viscosity_3_T_peak_in_GeV"});
      music_hydro_ptr->set_parameter("bulk_viscosity_3_T_peak_in_GeV",
                                     bulk_peakT);
      double bulk_width = GetXMLElementDouble(
          {"Hydro", "MUSIC", "bulk_viscosity_3_width_in_GeV"});
      music_hydro_ptr->set_parameter("bulk_viscosity_3_width_in_GeV",
                                     bulk_width);
      double bulk_asy = GetXMLElementDouble(
          {"Hydro", "MUSIC", "bulk_viscosity_3_lambda_asymm"});
      music_hydro_ptr->set_parameter("bulk_viscosity_3_lambda_asymm", bulk_asy);
    } else if (flag_bulkvis == 2) {
      double bulk_norm = GetXMLElementDouble(
          {"Hydro", "MUSIC", "bulk_viscosity_2_normalisation"});
      music_hydro_ptr->set_parameter("bulk_viscosity_2_normalisation",
                                     bulk_norm);
      double bulk_width = GetXMLElementDouble(
          {"Hydro", "MUSIC", "bulk_viscosity_2_width_in_GeV"});
      music_hydro_ptr->set_parameter("bulk_viscosity_2_width_in_GeV",
                                     bulk_width);
      double bulk_T = GetXMLElementDouble(
          {"Hydro", "MUSIC", "bulk_viscosity_2_peak_in_GeV"});
      music_hydro_ptr->set_parameter("bulk_viscosity_2_peak_in_GeV", bulk_T);
    } else if (flag_bulkvis == 10) {
      double bulk_viscosity_10_max =
          GetXMLElementDouble({"Hydro", "MUSIC", "bulk_viscosity_10_max"});
      music_hydro_ptr->set_parameter("bulk_viscosity_10_max",
                                     bulk_viscosity_10_max);
      double bulk_viscosity_10_max_muB0p4 = GetXMLElementDouble(
          {"Hydro", "MUSIC", "bulk_viscosity_10_max_muB0p4"});
      if (bulk_viscosity_10_max_muB0p4 < 0) {
        // set to bulk_viscosity_10_max
        bulk_viscosity_10_max_muB0p4 = bulk_viscosity_10_max;
      }
      music_hydro_ptr->set_parameter("bulk_viscosity_10_max_muB0p4",
                                     bulk_viscosity_10_max_muB0p4);
      double bulk_viscosity_10_max_muB0p2 = GetXMLElementDouble(
          {"Hydro", "MUSIC", "bulk_viscosity_10_max_muB0p2"});
      if (bulk_viscosity_10_max_muB0p2 < 0) {
        // set to (bulk_viscosity_10_max + bulk_viscosity_10_max_muB0p4)/2
        bulk_viscosity_10_max_muB0p2 =
            (bulk_viscosity_10_max + bulk_viscosity_10_max_muB0p4) / 2.;
      }
      music_hydro_ptr->set_parameter("bulk_viscosity_10_max_muB0p2",
                                     bulk_viscosity_10_max_muB0p2);
      double bulk_viscosity_10_width_high = GetXMLElementDouble(
          {"Hydro", "MUSIC", "bulk_viscosity_10_width_high"});
      music_hydro_ptr->set_parameter("bulk_viscosity_10_width_high",
                                     bulk_viscosity_10_width_high);
      double bulk_viscosity_10_width_low = GetXMLElementDouble(
          {"Hydro", "MUSIC", "bulk_viscosity_10_width_low"});
      music_hydro_ptr->set_parameter("bulk_viscosity_10_width_low",
                                     bulk_viscosity_10_width_low);
      double bulk_viscosity_10_T_peak =
          GetXMLElementDouble({"Hydro", "MUSIC", "bulk_viscosity_10_T_peak"});
      music_hydro_ptr->set_parameter("bulk_viscosity_10_T_peak",
                                     bulk_viscosity_10_T_peak);
      double bulk_viscosity_10_T_peak_muBcurv = GetXMLElementDouble(
          {"Hydro", "MUSIC", "bulk_viscosity_10_T_peak_muBcurv"});
      music_hydro_ptr->set_parameter("bulk_viscosity_10_T_peak_muBcurv",
                                     bulk_viscosity_10_T_peak_muBcurv);
    }
  }

  int flag_secondorderTerms =
      GetXMLElementInt({"Hydro", "MUSIC", "Include_second_order_terms"});
  if (flag_secondorderTerms == 1) {
    music_hydro_ptr->set_parameter("Include_second_order_terms", 1);
  }
  int flag_include_Rhob = GetXMLElementInt({"Hydro", "MUSIC", "Include_Rhob"});
  music_hydro_ptr->set_parameter("Include_Rhob", flag_include_Rhob);
  int flag_include_QS = GetXMLElementInt({"Hydro", "MUSIC", "Include_QS"});
  music_hydro_ptr->set_parameter("Include_QS", flag_include_QS);

  int use_eps_for_freeze_out =
      GetXMLElementInt({"Hydro", "MUSIC", "use_eps_for_freeze_out"});
  music_hydro_ptr->set_parameter("use_eps_for_freeze_out",
                                 use_eps_for_freeze_out);
  if (use_eps_for_freeze_out == 0) {
    freezeout_temperature =
        GetXMLElementDouble({"Hydro", "MUSIC", "freezeout_temperature"});
    if (freezeout_temperature > 0.05) {
      music_hydro_ptr->set_parameter("T_freeze", freezeout_temperature);
    } else {
      JSWARN << "The input freeze-out temperature is too low! T_frez = "
             << freezeout_temperature << " GeV!";
      exit(1);
    }
  } else {
    double eps_switch = GetXMLElementDouble({"Hydro", "MUSIC", "eps_switch"});
    music_hydro_ptr->set_parameter("eps_switch", eps_switch);
  }
  int freezeout_lowtemp_flag =
      GetXMLElementInt({"Hydro", "MUSIC", "Do_FreezeOut_lowtemp"});
  music_hydro_ptr->set_parameter("Do_FreezeOut_lowtemp",
                                 freezeout_lowtemp_flag);
  int average_surface_over_this_many_time_steps = GetXMLElementInt(
      {"Hydro", "MUSIC", "average_surface_over_this_many_time_steps"});
  music_hydro_ptr->set_parameter("average_surface_over_this_many_time_steps",
                                 average_surface_over_this_many_time_steps);

  music_hydro_ptr->check_parameters();
}

int MpiMusic::InitializeHydroEnergyProfile() {
  VERBOSE(8);
  JSINFO << "Initialize density profiles in MUSIC ...";
  int status = 0;
  std::vector<double> entropy_density = ini->GetEntropyDensityDistribution();
  double dx = ini->GetXStep();
  double dy = ini->GetYStep();
  double dz = ini->GetZStep();
  double z_max = ini->GetZMax();
  int nx = ini->GetXSize();
  int ny = ini->GetYSize();
  int nz = ini->GetZSize();

  // need further improvement to accept multiple source term objects
  // this is a temporary solution
  music_hydro_ptr->add_hydro_source_terms(hydro_source_terms_ptr);

  if (initialProfile_ == 13 || initialProfile_ == 131) {
    auto QCDStringList = ini->GetQCDStringList();
    JSINFO << "Setting up MUSIC string source terms from "
           << QCDStringList.size() << " QCD strings.";
    if (QCDStringList.size() == 0) {
      status = -1;
    } else {
      music_hydro_ptr->generate_hydro_source_terms(QCDStringList);
      music_hydro_ptr->initialize_hydro_xscape(nx, ny, nz, dx, dy, dz);
      hydro_source_terms_ptr->set_hydro_dtau(
          music_hydro_ptr->get_hydro_dtau_grid());
    }
  } else if (pre_eq_ptr == nullptr) {
    JSINFO << "Setting up the hydro without pre-equilibrium module ...";
    music_hydro_ptr->initialize_hydro_xscape(nx, ny, nz, dx, dy, dz);
    hydro_source_terms_ptr->set_hydro_dtau(
        music_hydro_ptr->get_hydro_dtau_grid());
  } else {
    music_hydro_ptr->generate_hydro_source_terms();
    double tau0 = pre_eq_ptr->GetPreequilibriumEndTime();
    JSINFO << "Hydro initial time  tau0 = " << tau0 << " fm";
    music_hydro_ptr->initialize_hydro_from_jetscape_preequilibrium_vectors(
        tau0, dx, dz, z_max, nz, pre_eq_ptr->e_, pre_eq_ptr->P_,
        pre_eq_ptr->utau_, pre_eq_ptr->ux_, pre_eq_ptr->uy_, pre_eq_ptr->ueta_,
        pre_eq_ptr->pi00_, pre_eq_ptr->pi01_, pre_eq_ptr->pi02_,
        pre_eq_ptr->pi03_, pre_eq_ptr->pi11_, pre_eq_ptr->pi12_,
        pre_eq_ptr->pi13_, pre_eq_ptr->pi22_, pre_eq_ptr->pi23_,
        pre_eq_ptr->pi33_, pre_eq_ptr->bulk_Pi_);
  }

  if (pre_eq_ptr == nullptr &&
      (initialProfile_ != 13 && initialProfile_ != 131 &&
       initialProfile_ != 43)) {
    JSWARN << "Missing the pre-equilibrium module ...";
    exit(1);
  }
  if (pre_eq_ptr == nullptr && flag_preEq_output_evo_to_memory == 1 &&
      initialProfile_ != 43) {
    JSWARN << "The pre-equilibrium module is not initialized! If you want to "
           << "run hydro with InitialProfile = 13 or 131 (3D-Glauber), please "
           << "set Preequilibrium/evolutionInMemory = 0 in the XML file.";
    exit(1);
  }

  JSINFO << "Initial density profile dx = " << dx << " fm";
  JSINFO << "Number of source terms: "
         << hydro_source_terms_ptr->get_number_of_sources();
  JSINFO << "Total E sources = "
         << hydro_source_terms_ptr->get_total_E_of_sources() << " GeV.";
  JSINFO << "Total net baryon number of sources = "
         << hydro_source_terms_ptr->get_net_baryon_number_of_sources()
         << ", total net electric charge = "
         << hydro_source_terms_ptr->get_net_electric_charge_of_sources()
         << ", total net strangeness = "
         << hydro_source_terms_ptr->get_net_strangeness_of_sources() << ".";
  if (status == 0)
    hydro_status = INITIALIZED;
  return (status);
}

void MpiMusic::EvolveHydroUpto(const double tauEnd) {
  if (hydro_status == NOT_START) {
    int ini_status = InitializeHydroEnergyProfile();
    if (ini_status != 0) {
      hydro_status = FINISHED;
      return;
    }
    music_hydro_ptr->prepare_run_hydro_one_time_step();
    hydro_source_terms_ptr->set_source_tau_max(GetSourceTermTauMax());
  }

  if (hydro_status != FINISHED) {
    int status = music_hydro_ptr->run_hydro_upto(tauEnd);
    if (status != 0) {
      hydro_status = FINISHED;
    }
  }
  // PassHydroSurfaceToFramework();
}

void MpiMusic::CalculateTime() {
  VERBOSE(2) << "MpiMusic::CalculateTime() main Clock = "
             << GetMainClock()->GetCurrentTime() << " fm/c ...";
  EvolveHydroUpto(GetMainClock()->GetCurrentTime());
}

void MpiMusic::ExecTime() {
  VERBOSE(2) << "MpiMusic::ExecTime() main Clock = "
             << GetMainClock()->GetCurrentTime() << " fm/c ...";
  VERBOSE(2) << "Energy sources ="
             << hydro_source_terms_ptr->get_total_E_of_sources();

  // Pass the FO surface for the current time step to framework
  if (hydro_status == INITIALIZED) {
    VERBOSE(2) << "Passing hydro surface cells to JETSCAPE ... ";
    PassHydroSurfaceToFramework();
  }
}

void MpiMusic::EvolveHydro() {
  if (hydro_status == NOT_START) {
    int ini_status = InitializeHydroEnergyProfile();
    if (ini_status != 0) {
      hydro_status = FINISHED;
      if (flag_surface_in_memory == 1) {
        clearSurfaceCellVector();
      }
      if (flag_output_evo_to_memory == 1) {
        clear_up_evolution_data();
      }
      return;
    }
  }

  has_source_terms = false;
  if (hydro_source_terms_ptr->get_number_of_sources() > 0) {
    has_source_terms = true;
  }

  if (flag_preEq_output_evo_to_memory == 1 && pre_eq_ptr != nullptr &&
      initialProfile_ == 42) {
    double tau0 = pre_eq_ptr->GetPreequilibriumEndTime();
    JSINFO << "Hydro initial time set by pre-equilibrium module tau0 = " << tau0
           << " fm/c";
    if (flag_output_evo_to_memory == 1) {
      // need to ensure preEq and hydro use the same dtau so that
      // the combined evolution history file is properly set
      double dtau = pre_eq_ptr->GetPreequilibriumEvodtau();
      JSINFO << "Reset MUSIC dtau by PreEq module: dtau = " << dtau << " fm/c";
      music_hydro_ptr->set_parameter("dtau", dtau);
      if (!has_source_terms) {
        // only the preEq evo with the first hydro without source term
        // will be stored in memory for jet energy loss calculations
        clear_up_evolution_data();
        PassPreEqEvolutionHistoryToFramework();
      }
    }
  }

  hydro_status = INITIALIZED;

  if (hydro_status == INITIALIZED) {
    JSINFO << "running MUSIC ...";
    music_hydro_ptr->run_hydro();
    hydro_status = FINISHED;
  }

  if (flag_output_evo_to_memory == 1) {
    const bool xscape_string_source_history =
        has_source_terms && (initialProfile_ == 13 || initialProfile_ == 131);
    if (!has_source_terms || xscape_string_source_history) {
      // For InitialProfile 13/131, source terms are the 3D-Glauber string
      // initial condition. They must still be copied for MATTER energy-loss
      // queries; otherwise MATTER falls back to live MUSIC memory after the
      // framework history remains empty.
      if (flag_preEq_output_evo_to_memory == 0) {
        clear_up_evolution_data();
      }
      PassHydroEvolutionHistoryToFramework();
      JSINFO << "Number of fluid cells received by JETSCAPE: "
             << bulk_info.data.size();
      WriteHydroHistoryQA("after_PassHydroEvolutionHistoryToFramework");
    } else {
      JSWARN << "Skipping MUSIC hydro-history copy because source terms are "
             << "present for InitialProfile=" << initialProfile_
             << ". This workflow will not provide MATTER in-medium history.";
      WriteHydroHistoryQA("skipped_source_terms");
    }
  }

  if (flag_output_evo_to_file == 1) {
    // add hydro_id to the hydro evolution filename
    std::ostringstream system_command;
    system_command << "mv evolution_all_xyeta.dat "
                   << "evolution_all_xyeta_" << GetId() << ".dat";
    system(system_command.str().c_str());
  }

  if (flag_surface_in_memory == 1) {
    clearSurfaceCellVector();
    PassHydroSurfaceToFramework();
  } else {
    collect_freeze_out_surface();
  }

  if (hydro_status == FINISHED && doCooperFrye == 1) {
    music_hydro_ptr->run_Cooper_Frye();
  }
}

void MpiMusic::collect_freeze_out_surface() {
  std::ostringstream surface_filename;
  surface_filename << "surface_" << GetId() << ".dat";

  const std::string merged_surface = surface_filename.str();
  const std::string iss_surface = "surface.dat";

  std::remove(iss_surface.c_str());
  std::remove(merged_surface.c_str());

  glob_t glob_result;
  const int glob_status = glob("surface_eps*.dat", 0, nullptr, &glob_result);
  if (glob_status != 0 || glob_result.gl_pathc == 0) {
    globfree(&glob_result);
    JSWARN << "No MUSIC freezeout surface files matched surface_eps*.dat; "
           << "not creating surface.dat.";
    throw std::runtime_error(
        "MUSIC freezeout produced no surface_eps*.dat files");
  }

  std::ofstream merged(merged_surface, std::ios::binary | std::ios::out);
  if (!merged) {
    globfree(&glob_result);
    throw std::runtime_error("Could not create " + merged_surface);
  }

  std::size_t files_merged = 0;
  std::size_t bytes_merged = 0;
  std::vector<std::string> surface_files;
  for (std::size_t i = 0; i < glob_result.gl_pathc; ++i) {
    surface_files.push_back(glob_result.gl_pathv[i]);
  }
  std::sort(surface_files.begin(), surface_files.end());

  for (const auto &path : surface_files) {
    std::ifstream input(path, std::ios::binary | std::ios::in);
    if (!input) {
      JSWARN << "Skipping unreadable MUSIC surface fragment: " << path;
      continue;
    }
    input.seekg(0, std::ios::end);
    const std::streamoff file_size = input.tellg();
    input.seekg(0, std::ios::beg);
    if (file_size <= 0) {
      JSWARN << "Skipping empty MUSIC surface fragment: " << path;
      continue;
    }
    merged << input.rdbuf();
    bytes_merged += static_cast<std::size_t>(file_size);
    files_merged++;
  }
  merged.close();
  globfree(&glob_result);

  if (files_merged == 0 || bytes_merged == 0) {
    std::remove(merged_surface.c_str());
    JSWARN << "All MUSIC surface fragments were empty or unreadable; "
           << "not creating surface.dat.";
    throw std::runtime_error("MUSIC freezeout surface merge was empty");
  }

  std::ifstream merged_in(merged_surface, std::ios::binary | std::ios::in);
  std::ofstream iss_out(iss_surface, std::ios::binary | std::ios::out);
  if (!merged_in || !iss_out) {
    throw std::runtime_error("Could not publish merged MUSIC surface.dat");
  }
  iss_out << merged_in.rdbuf();
  iss_out.close();

  for (const auto &path : surface_files) {
    std::remove(path.c_str());
  }

  JSINFO << "Merged " << files_merged << " MUSIC surface fragment files into "
         << merged_surface << " and surface.dat (" << bytes_merged
         << " bytes).";
}

void MpiMusic::SetPreEqGridInfo() {
  bulk_info.tau_min = pre_eq_ptr->GetPreequilibriumStartTime();
  bulk_info.dtau = pre_eq_ptr->GetPreequilibriumEvodtau();
  JSINFO << "Pre-equilibrium evolution: tau_0 = " << bulk_info.tau_min
         << " fm/c, dtau = " << bulk_info.dtau << " fm/c.";
}

void MpiMusic::SetHydroGridInfo() {
  bulk_info.neta = music_hydro_ptr->get_neta();
  bulk_info.nx = music_hydro_ptr->get_nx();
  bulk_info.ny = music_hydro_ptr->get_ny();
  bulk_info.x_min = -music_hydro_ptr->get_hydro_x_max();
  bulk_info.dx = music_hydro_ptr->get_hydro_dx();
  bulk_info.y_min = -music_hydro_ptr->get_hydro_y_max();
  bulk_info.dy = music_hydro_ptr->get_hydro_dy();
  bulk_info.eta_min = -music_hydro_ptr->get_hydro_eta_max();
  bulk_info.deta = music_hydro_ptr->get_hydro_deta();
  JSINFO << "MUSIC hydro grid passed to JETSCAPE: ntau="
         << music_hydro_ptr->get_ntau() << " nx=" << bulk_info.nx
         << " ny=" << bulk_info.ny << " neta=" << bulk_info.neta
         << " dx=" << bulk_info.dx << " dy=" << bulk_info.dy
         << " deta=" << bulk_info.deta << ".";

  bulk_info.boost_invariant =
      music_hydro_ptr->is_boost_invariant() || bulk_info.neta <= 1;
  if (bulk_info.neta <= 1 && !music_hydro_ptr->is_boost_invariant()) {
    JSWARN << "MUSIC hydro history has neta=" << bulk_info.neta
           << " but is_boost_invariant=false. Treating the copied JETSCAPE "
           << "history as eta-collapsed for hydro-cell interpolation.";
  }

  if (flag_preEq_output_evo_to_memory == 0) {
    bulk_info.tau_min = music_hydro_ptr->get_hydro_tau0();
    bulk_info.dtau = music_hydro_ptr->get_hydro_dtau();
    bulk_info.ntau = music_hydro_ptr->get_ntau();
  } else {
    bulk_info.ntau = music_hydro_ptr->get_ntau() + pre_eq_ptr->get_ntau();
  }
}

void MpiMusic::PassHydroSurfaceToFramework() {
  JSINFO << "Passing hydro surface cells to JETSCAPE ... ";
  auto number_of_cells = music_hydro_ptr->get_number_of_surface_cells();
  JSINFO << "Total number of MUSIC surface cells: " << number_of_cells;
  SurfaceCell surfaceCell_i;
  for (int i = 0; i < number_of_cells; i++) {
    SurfaceCellInfo surface_cell_info;
    music_hydro_ptr->get_surface_cell_with_index(i, surfaceCell_i);
    surface_cell_info.tau = surfaceCell_i.xmu[0];
    surface_cell_info.x = surfaceCell_i.xmu[1];
    surface_cell_info.y = surfaceCell_i.xmu[2];
    surface_cell_info.eta = surfaceCell_i.xmu[3];
    double u[4];
    for (int j = 0; j < 4; j++) {
      surface_cell_info.d3sigma_mu[j] = surfaceCell_i.d3sigma_mu[j];
      surface_cell_info.umu[j] = surfaceCell_i.umu[j];
    }
    surface_cell_info.energy_density = surfaceCell_i.energy_density;
    surface_cell_info.temperature = surfaceCell_i.temperature;
    surface_cell_info.pressure = surfaceCell_i.pressure;
    surface_cell_info.baryon_density = surfaceCell_i.rho_b;
    surface_cell_info.electric_charge_density = surfaceCell_i.rho_q;
    surface_cell_info.strangeness_density = surfaceCell_i.rho_s;
    surface_cell_info.mu_B = surfaceCell_i.mu_B;
    surface_cell_info.mu_Q = surfaceCell_i.mu_Q;
    surface_cell_info.mu_S = surfaceCell_i.mu_S;
    for (int j = 0; j < 10; j++) {
      surface_cell_info.pi[j] = surfaceCell_i.shear_pi[j];
    }
    surface_cell_info.bulk_Pi = surfaceCell_i.bulk_Pi;
    StoreSurfaceCell(surface_cell_info);
  }
  music_hydro_ptr->clear_surface_cell_vector();
}

void MpiMusic::PassPreEqEvolutionHistoryToFramework() {
  JSINFO << "Passing pre-equilibrium evolution information to JETSCAPE ... ";
  auto number_of_cells = pre_eq_ptr->get_number_of_fluid_cells();
  JSINFO << "Total number of pre-equilibrium fluid cells: " << number_of_cells;

  SetPreEqGridInfo();

  for (int i = 0; i < number_of_cells; i++) {
    std::unique_ptr<FluidCellInfo> fluid_cell_info_ptr(new FluidCellInfo);
    pre_eq_ptr->get_fluid_cell_with_index(i, fluid_cell_info_ptr);
    StoreHydroEvolutionHistory(fluid_cell_info_ptr);
  }
  pre_eq_ptr->clear_evolution_data();
}

void MpiMusic::PassHydroEvolutionHistoryToFramework() {
  JSINFO << "Passing hydro evolution information to JETSCAPE ... ";
  auto number_of_cells = music_hydro_ptr->get_number_of_fluid_cells();
  JSINFO << "Total number of MUSIC fluid cells: " << number_of_cells;

  SetHydroGridInfo();

  fluidCell *fluidCell_ptr = new fluidCell;
  for (int i = 0; i < number_of_cells; i++) {
    std::unique_ptr<FluidCellInfo> fluid_cell_info_ptr(new FluidCellInfo);
    music_hydro_ptr->get_fluid_cell_with_index(i, fluidCell_ptr);

    fluid_cell_info_ptr->energy_density = fluidCell_ptr->ed;
    fluid_cell_info_ptr->entropy_density = fluidCell_ptr->sd;
    fluid_cell_info_ptr->temperature = fluidCell_ptr->temperature;
    fluid_cell_info_ptr->pressure = fluidCell_ptr->pressure;
    fluid_cell_info_ptr->vx = fluidCell_ptr->vx;
    fluid_cell_info_ptr->vy = fluidCell_ptr->vy;
    fluid_cell_info_ptr->vz = fluidCell_ptr->vz;
    fluid_cell_info_ptr->mu_B = 0.0;
    fluid_cell_info_ptr->mu_C = 0.0;
    fluid_cell_info_ptr->mu_S = 0.0;
    fluid_cell_info_ptr->qgp_fraction = 0.0;
    for (int i = 0; i < 4; i++) {
      for (int j = 0; j < 4; j++) {
        fluid_cell_info_ptr->pi[i][j] = fluidCell_ptr->pi[i][j];
      }
    }
    fluid_cell_info_ptr->bulk_Pi = fluidCell_ptr->bulkPi;
    StoreHydroEvolutionHistory(fluid_cell_info_ptr);
  }
  delete fluidCell_ptr;
  music_hydro_ptr->clear_hydro_info_from_memory();
}

void MpiMusic::GetHydroInfo(
    Jetscape::real t, Jetscape::real x, Jetscape::real y, Jetscape::real z,
    std::unique_ptr<FluidCellInfo> &fluid_cell_info_ptr) {
  if (bulk_info.data.size() > 0) {
    GetHydroInfo_JETSCAPE(t, x, y, z, fluid_cell_info_ptr);
  } else if (flag_output_evo_to_memory == 1) {
    GetHydroInfo_MUSIC(t, x, y, z, fluid_cell_info_ptr);
  } else {
    GetHydroInfo_JETSCAPE(t, x, y, z, fluid_cell_info_ptr);
  }
}

void MpiMusic::GetHydroInfo_JETSCAPE(
    Jetscape::real t, Jetscape::real x, Jetscape::real y, Jetscape::real z,
    std::unique_ptr<FluidCellInfo> &fluid_cell_info_ptr) {
  auto temp = bulk_info.get_tz(t, x, y, z);
  fluid_cell_info_ptr = std::unique_ptr<FluidCellInfo>(new FluidCellInfo(temp));
  RecordHydroQueryPath("JETSCAPE", t, x, y, z, *fluid_cell_info_ptr);
}

void MpiMusic::GetHydroInfo_MUSIC(
    Jetscape::real t, Jetscape::real x, Jetscape::real y, Jetscape::real z,
    std::unique_ptr<FluidCellInfo> &fluid_cell_info_ptr) {
  fluid_cell_info_ptr = Jetscape::make_unique<FluidCellInfo>();
  fluidCell *fluidCell_ptr = new fluidCell;
  music_hydro_ptr->get_hydro_info(x, y, z, t, fluidCell_ptr);
  fluid_cell_info_ptr->energy_density = fluidCell_ptr->ed;
  fluid_cell_info_ptr->entropy_density = fluidCell_ptr->sd;
  fluid_cell_info_ptr->temperature = fluidCell_ptr->temperature;
  fluid_cell_info_ptr->pressure = fluidCell_ptr->pressure;
  fluid_cell_info_ptr->vx = fluidCell_ptr->vx;
  fluid_cell_info_ptr->vy = fluidCell_ptr->vy;
  fluid_cell_info_ptr->vz = fluidCell_ptr->vz;
  fluid_cell_info_ptr->mu_B = 0.0;
  fluid_cell_info_ptr->mu_C = 0.0;
  fluid_cell_info_ptr->mu_S = 0.0;
  fluid_cell_info_ptr->qgp_fraction = 0.0;

  for (int i = 0; i < 4; i++) {
    for (int j = 0; j < 4; j++) {
      fluid_cell_info_ptr->pi[i][j] = fluidCell_ptr->pi[i][j];
    }
  }
  fluid_cell_info_ptr->bulk_Pi = fluidCell_ptr->bulkPi;
  RecordHydroQueryPath("MUSIC_FALLBACK", t, x, y, z, *fluid_cell_info_ptr);
  delete fluidCell_ptr;
}

void MpiMusic::WriteHydroHistoryQA(const std::string &stage) const {
  std::ofstream qa("medium_activation_hydro_history_QA.txt", std::ios::app);
  if (!qa) {
    return;
  }
  double t_min = 0.0;
  double t_max = 0.0;
  double t_sum = 0.0;
  long long t_gt0 = 0;
  long long t_gt155 = 0;
  long long t_gt160 = 0;
  if (!bulk_info.data.empty()) {
    t_min = bulk_info.data.front().temperature;
    for (const auto &cell : bulk_info.data) {
      const double temp = cell.temperature;
      t_min = std::min(t_min, temp);
      t_max = std::max(t_max, temp);
      t_sum += temp;
      if (temp > 0.0) {
        t_gt0++;
      }
      if (temp > 0.155) {
        t_gt155++;
      }
      if (temp > 0.160) {
        t_gt160++;
      }
    }
  }
  const double t_mean =
      bulk_info.data.empty() ? 0.0 : t_sum / bulk_info.data.size();
  qa << "MUSIC/JETSCAPE hydro history QA\n"
     << "stage " << stage << "\n"
     << "initialProfile " << initialProfile_ << "\n"
     << "has_source_terms " << has_source_terms << "\n"
     << "flag_output_evo_to_memory " << flag_output_evo_to_memory << "\n"
     << "cells " << bulk_info.data.size() << "\n"
     << "ntau " << bulk_info.ntau << "\n"
     << "nx " << bulk_info.nx << "\n"
     << "ny " << bulk_info.ny << "\n"
     << "neta " << bulk_info.neta << "\n"
     << "tau0 " << bulk_info.tau_min << "\n"
     << "dtau " << bulk_info.dtau << "\n"
     << "tau_max " << bulk_info.TauMax() << "\n"
     << "x_min " << bulk_info.x_min << "\n"
     << "x_max " << bulk_info.XMax() << "\n"
     << "y_min " << bulk_info.y_min << "\n"
     << "y_max " << bulk_info.YMax() << "\n"
     << "eta_min " << bulk_info.eta_min << "\n"
     << "eta_max " << bulk_info.EtaMax() << "\n"
     << "temperature_min_GeV " << t_min << "\n"
     << "temperature_mean_GeV " << t_mean << "\n"
     << "temperature_max_GeV " << t_max << "\n"
     << "cells_T_gt_0 " << t_gt0 << "\n"
     << "cells_T_gt_0p155 " << t_gt155 << "\n"
     << "cells_T_gt_0p160 " << t_gt160 << "\n"
     << "----\n";
}

void MpiMusic::RecordHydroQueryPath(const std::string &source, Jetscape::real t,
                                    Jetscape::real x, Jetscape::real y,
                                    Jetscape::real z,
                                    const FluidCellInfo &cell) const {
  if (source == "JETSCAPE") {
    hydro_query_framework_count++;
  } else {
    hydro_query_music_fallback_count++;
  }
  if (bulk_info.data.empty()) {
    hydro_query_no_history_count++;
  }

  double tau = 0.0;
  double eta = 0.0;
  bool in_light_cone = false;
  if (t * t > z * z && t != z) {
    in_light_cone = true;
    tau = std::sqrt(t * t - z * z);
    eta = 0.5 * std::log((t + z) / (t - z));
  }
  bool inside = in_light_cone && !bulk_info.data.empty();
  if (!in_light_cone) {
    inside = false;
  } else {
    if (tau < bulk_info.tau_min) {
      hydro_query_before_tau0_count++;
      inside = false;
    }
    if (tau > bulk_info.TauMax()) {
      hydro_query_after_taumax_count++;
      inside = false;
    }
    if (x < bulk_info.x_min || x > bulk_info.XMax() || y < bulk_info.y_min ||
        y > bulk_info.YMax()) {
      hydro_query_outside_xy_count++;
      inside = false;
    }
    if (!bulk_info.boost_invariant &&
        (eta < bulk_info.eta_min || eta > bulk_info.EtaMax())) {
      hydro_query_outside_eta_count++;
      inside = false;
    }
  }

  if (inside) {
    hydro_query_inside_count++;
    if (cell.temperature > 0.0) {
      hydro_query_inside_T_gt0_count++;
    }
    if (cell.temperature >= 0.155) {
      hydro_query_inside_T_ge155_count++;
    }
    if (cell.temperature >= 0.160) {
      hydro_query_inside_T_ge160_count++;
    }
  }

  if (hydro_query_path_samples < 20) {
    std::ofstream samples("medium_activation_hydro_query_samples.txt",
                          std::ios::app);
    if (samples) {
      samples << "sample " << hydro_query_path_samples << " source " << source
              << " t " << t << " x " << x << " y " << y << " z " << z
              << " tau " << tau << " eta " << eta << " inside " << inside
              << " T " << cell.temperature << "\n";
    }
    hydro_query_path_samples++;
  }
  if ((hydro_query_framework_count + hydro_query_music_fallback_count) % 5000 ==
      0) {
    WriteHydroQueryPathQA();
  }
}

void MpiMusic::WriteHydroQueryPathQA() const {
  std::ofstream qa("medium_activation_hydro_query_path_QA.txt");
  if (!qa) {
    return;
  }
  qa << "MUSIC/JETSCAPE hydro query path QA\n"
     << "framework_queries " << hydro_query_framework_count << "\n"
     << "music_fallback_queries " << hydro_query_music_fallback_count << "\n"
     << "no_framework_history_queries " << hydro_query_no_history_count << "\n"
     << "before_tau0_queries " << hydro_query_before_tau0_count << "\n"
     << "after_tau_max_queries " << hydro_query_after_taumax_count << "\n"
     << "outside_xy_queries " << hydro_query_outside_xy_count << "\n"
     << "outside_eta_queries " << hydro_query_outside_eta_count << "\n"
     << "inside_range_queries " << hydro_query_inside_count << "\n"
     << "inside_range_T_gt_0 " << hydro_query_inside_T_gt0_count << "\n"
     << "inside_range_T_ge_0p155 " << hydro_query_inside_T_ge155_count << "\n"
     << "inside_range_T_ge_0p160 " << hydro_query_inside_T_ge160_count << "\n"
     << "history_cells " << bulk_info.data.size() << "\n"
     << "ntau " << bulk_info.ntau << "\n"
     << "nx " << bulk_info.nx << "\n"
     << "ny " << bulk_info.ny << "\n"
     << "neta " << bulk_info.neta << "\n"
     << "tau0 " << bulk_info.tau_min << "\n"
     << "dtau " << bulk_info.dtau << "\n"
     << "tau_max " << bulk_info.TauMax() << "\n";
}

bool MpiMusic::update_music_input_parameter(const std::string &filename,
                                            const std::string &key,
                                            int new_value) {
  std::ifstream infile(filename);
  if (!infile.is_open()) {
    std::cerr << "Error opening input file: " << filename << "\n";
    return false;
  }

  std::ostringstream buffer;
  std::string line;
  bool found = false;

  std::regex pattern("^\\s*" + key + R"(\s+([-+]?[0-9]*\.?[0-9]+)(\s+|$))");

  while (std::getline(infile, line)) {
    std::smatch match;
    if (std::regex_search(line, match, pattern)) {
      found = true;
      std::string comment;
      size_t comment_pos = line.find("#");
      if (comment_pos != std::string::npos) {
        comment = line.substr(comment_pos);
      }
      std::ostringstream newline;
      newline << key << " " << new_value;
      if (!comment.empty()) {
        newline << " " << comment;
      }
      buffer << newline.str() << "\n";
    } else {
      buffer << line << "\n";
    }
  }
  infile.close();

  if (!found) {
    std::cerr << "Parameter \"" << key << "\" not found in " << filename
              << "\n";
    return false;
  }

  std::ofstream outfile(filename);
  if (!outfile.is_open()) {
    std::cerr << "Error writing to file: " << filename << "\n";
    return false;
  }
  outfile << buffer.str();
  outfile.close();

  return true;
}
