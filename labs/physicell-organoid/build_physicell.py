"""Prepare the PhysiCell 1.14.2 cancer project as an organoid assay executable."""

import argparse
import subprocess
from pathlib import Path

HETEROGENEITY_CODE = r"""
	// Assign a seeded treatment phenotype to each tumor cell. Branches in Synthetic Lab
	// replay the same PhysiCell seed, so untreated and treated wells share the draw.
	Cell_Definition* pTumor = find_cell_definition( "cancer cell" );
	double resistant_fraction = parameters.doubles( "resistant_fraction" );
	double sensitive_damage_rate = parameters.doubles( "sensitive_damage_rate" );
	double resistant_damage_rate = parameters.doubles( "resistant_damage_rate" );
	double sensitive_repair_rate = parameters.doubles( "sensitive_repair_rate" );
	double resistant_repair_rate = parameters.doubles( "resistant_repair_rate" );
	double drug_death_rate = parameters.doubles( "drug_death_rate" );
	for( int i = 0; i < all_cells->size(); i++ )
	{
		Cell* pCell = (*all_cells)[i];
		if( pCell->type != pTumor->type )
		{ continue; }
		bool resistant = UniformRandom() < resistant_fraction;
		set_single_behavior( pCell, "custom:damage_rate",
			resistant ? resistant_damage_rate : sensitive_damage_rate );
		set_single_behavior( pCell, "custom:repair_rate",
			resistant ? resistant_repair_rate : sensitive_repair_rate );
		set_single_behavior( pCell, "custom:drug_death_rate", drug_death_rate );
	}

"""

TREATMENT_SETUP = r"""
	int therapeutic_index = microenvironment.find_density_index( "therapeutic" );
	if( therapeutic_index < 0 )
	{ throw std::runtime_error( "therapeutic substrate is not defined" ); }
	double treatment_start_min = parameters.doubles( "treatment_start_min" );
	double treatment_end_min = parameters.doubles( "treatment_end_min" );
	double treatment_concentration = parameters.doubles( "treatment_concentration" );
"""

TREATMENT_BOUNDARY = r"""
			// Culture-medium exposure is represented by a time-dependent treatment
			// concentration on the outer Dirichlet boundary. BioFVM resolves penetration.
			double bath_concentration = 0.0;
			if( PhysiCell_globals.current_time >= treatment_start_min &&
				PhysiCell_globals.current_time < treatment_end_min )
			{ bath_concentration = treatment_concentration; }
			for( int voxel_index = 0;
				voxel_index < microenvironment.mesh.voxels.size(); voxel_index++ )
			{
				if( microenvironment.mesh.voxels[voxel_index].is_Dirichlet )
				{
					microenvironment.update_dirichlet_node(
						voxel_index, therapeutic_index, bath_concentration );
				}
			}

"""

SUMMARY_CODE = r"""
	// Write compact endpoint observables and the cell-resolved final state for the
	// Synthetic Lab adapter. PhysiCell's native final MultiCellDS output is retained.
	Cell_Definition* pTumor = find_cell_definition( "cancer cell" );
	double hypoxia_threshold = parameters.doubles( "hypoxia_threshold" );
	double resistance_threshold = 0.5 * (
		parameters.doubles( "sensitive_repair_rate" ) +
		parameters.doubles( "resistant_repair_rate" ) );
	int total_cells = 0;
	int viable_cells = 0;
	int apoptotic_cells = 0;
	int necrotic_cells = 0;
	int resistant_viable_cells = 0;
	int hypoxic_viable_cells = 0;
	double oxygen_sum = 0.0;
	double therapeutic_sum = 0.0;
	double damage_sum = 0.0;
	double radial_extent = 0.0;

	std::string cells_path = PhysiCell_settings.folder + "/cells.csv";
	std::ofstream cells_file( cells_path.c_str() );
	cells_file << "x_um,y_um,z_um,dead,apoptotic,necrotic,resistant,oxygen_mmhg,therapeutic,damage\n";
	for( int i = 0; i < all_cells->size(); i++ )
	{
		Cell* pCell = (*all_cells)[i];
		if( pCell->type != pTumor->type )
		{ continue; }
		total_cells++;
		double dead = get_single_signal( pCell, "dead" );
		double apoptotic = get_single_signal( pCell, "apoptotic" );
		double necrotic = get_single_signal( pCell, "necrotic" );
		double oxygen = get_single_signal( pCell, "oxygen" );
		double therapeutic = get_single_signal( pCell, "therapeutic" );
		double damage = get_single_signal( pCell, "damage" );
		double repair = get_single_signal( pCell, "custom:repair_rate" );
		bool resistant = repair > resistance_threshold;
		if( apoptotic > 0.5 )
		{ apoptotic_cells++; }
		else if( necrotic > 0.5 )
		{ necrotic_cells++; }
		else if( dead < 0.5 )
		{
			viable_cells++;
			if( resistant )
			{ resistant_viable_cells++; }
			if( oxygen < hypoxia_threshold )
			{ hypoxic_viable_cells++; }
		}
		oxygen_sum += oxygen;
		therapeutic_sum += therapeutic;
		damage_sum += damage;
		double radius = sqrt(
			pCell->position[0] * pCell->position[0] +
			pCell->position[1] * pCell->position[1] +
			pCell->position[2] * pCell->position[2] ) +
			pCell->phenotype.geometry.radius;
		if( radius > radial_extent )
		{ radial_extent = radius; }
		cells_file << pCell->position[0] << "," << pCell->position[1] << ","
			<< pCell->position[2] << "," << (dead > 0.5) << ","
			<< (apoptotic > 0.5) << "," << (necrotic > 0.5) << ","
			<< resistant << "," << oxygen << "," << therapeutic << ","
			<< damage << "\n";
	}
	cells_file.close();

	double denominator = total_cells > 0 ? total_cells : 1;
	std::string summary_path = PhysiCell_settings.folder + "/summary.csv";
	std::ofstream summary_file( summary_path.c_str() );
	summary_file << "total_cells,viable_cells,apoptotic_cells,necrotic_cells,"
		<< "resistant_viable_cells,hypoxic_viable_cells,equivalent_diameter_um,"
		<< "mean_oxygen_mmhg,mean_therapeutic,mean_damage\n";
	summary_file << total_cells << "," << viable_cells << "," << apoptotic_cells
		<< "," << necrotic_cells << "," << resistant_viable_cells << ","
		<< hypoxic_viable_cells << "," << 2.0 * radial_extent << ","
		<< oxygen_sum / denominator << "," << therapeutic_sum / denominator
		<< "," << damage_sum / denominator << "\n";
	summary_file.close();

"""


def replace_once(text, old, new, path):
    if text.count(old) != 1:
        raise RuntimeError(f"Expected one patch point in {path}: {old!r}")
    return text.replace(old, new, 1)


def prepare(root):
    root = root.resolve()
    subprocess.run(["make", "cancer-biorobots-sample"], cwd=root, check=True)

    makefile = root / "Makefile"
    text = makefile.read_text(encoding="utf-8")
    text = replace_once(
        text,
        "PROGRAM_NAME := cancer_biorobots",
        "PROGRAM_NAME := organoid_therapy",
        makefile,
    )
    makefile.write_text(text, encoding="utf-8")

    custom = root / "custom_modules" / "custom.cpp"
    text = custom.read_text(encoding="utf-8")
    marker = "\t// load cells from your CSV file (if enabled)\n"
    text = replace_once(text, marker, HETEROGENEITY_CODE + marker, custom)
    custom.write_text(text, encoding="utf-8")

    main = root / "main.cpp"
    text = main.read_text(encoding="utf-8")
    text = replace_once(
        text,
        '\tdouble therapy_activation_time = parameters.doubles("therapy_activation_time"); \n',
        '\tdouble therapy_activation_time = parameters.doubles("therapy_activation_time"); \n'
        + TREATMENT_SETUP,
        main,
    )
    text = replace_once(text, "\t\t\t\tintroduce_biorobots();\n", "", main)
    marker = "\t\t\t// update the microenvironment\n"
    text = replace_once(text, marker, TREATMENT_BOUNDARY + marker, main)
    text = replace_once(text, "\n\treturn 0; \n}", "\n" + SUMMARY_CODE + "\treturn 0; \n}", main)
    main.write_text(text, encoding="utf-8")

    print(f"Prepared PhysiCell organoid project in {root}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("physicell_root", type=Path)
    args = parser.parse_args()
    prepare(args.physicell_root)


if __name__ == "__main__":
    main()
