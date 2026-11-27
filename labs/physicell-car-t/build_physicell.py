"""Prepare the PhysiCell 1.14.2 cancer-immune project as a CAR-T spheroid executable."""

import argparse
import subprocess
from pathlib import Path

INTRODUCE_IMMUNE_CELLS = r"""
void introduce_immune_cells( void )
{
	double tumor_radius = 0.0;
	Cell_Definition* pTumor = find_cell_definition( "cancer cell" );
	for( int i = 0; i < (*all_cells).size(); i++ )
	{
		Cell* pCell = (*all_cells)[i];
		if( pCell->type != pTumor->type )
		{ continue; }
		double radius = sqrt( norm_squared( pCell->position ) )
			+ pCell->phenotype.geometry.radius;
		if( radius > tumor_radius )
		{ tumor_radius = radius; }
	}
	if( tumor_radius <= 0.0 )
	{ tumor_radius = parameters.doubles( "tumor_radius" ); }

	std::cout << "current tumor radius: " << tumor_radius << std::endl;

	int number_of_immune_cells = parameters.ints( "number_of_immune_cells" );
	double radius_inner = tumor_radius
		+ parameters.doubles( "initial_min_immune_distance_from_tumor" );
	double radius_outer = radius_inner
		+ parameters.doubles( "thickness_of_immune_seeding_region" );
	double mean_radius = 0.5 * ( radius_inner + radius_outer );
	double std_radius = 0.33 * ( radius_outer - radius_inner ) / 2.0;

	for( int i = 0; i < number_of_immune_cells; i++ )
	{
		double theta = UniformRandom() * 6.283185307179586476925286766559;
		double phi = acos( 2.0 * UniformRandom() - 1.0 );
		double radius = NormalRandom( mean_radius, std_radius );
		Cell* pCell = create_cell( *pImmuneCell );
		pCell->assign_position(
			radius * cos( theta ) * sin( phi ),
			radius * sin( theta ) * sin( phi ),
			radius * cos( phi ) );
	}
	return;
}
"""

SETUP_TISSUE = r"""
void setup_tissue( void )
{
	double cell_radius = cell_defaults.phenotype.geometry.radius;
	double tumor_radius = parameters.doubles( "tumor_radius" );
	std::vector<std::vector<double>> positions =
		create_cell_sphere_positions( cell_radius, tumor_radius );

	double antigen_mean = parameters.doubles( "tumor_mean_antigen" );
	double antigen_sd = parameters.doubles( "tumor_antigen_sd" );
	double antigen_negative_fraction = parameters.doubles( "antigen_negative_fraction" );
	double antigen_saturation = parameters.doubles( "antigen_saturation" );

	std::cout << "creating " << positions.size()
		<< " closely-packed tumor cells ..." << std::endl;

	for( int i = 0; i < positions.size(); i++ )
	{
		Cell* pCell = create_cell();
		pCell->assign_position( positions[i] );
		double antigen = NormalRandom( antigen_mean, antigen_sd );
		if( UniformRandom() < antigen_negative_fraction )
		{ antigen = 0.0; }
		if( antigen < 0.0 )
		{ antigen = 0.0; }
		if( antigen > antigen_saturation )
		{ antigen = antigen_saturation; }

		// Keep proliferative fitness independent from CAR target abundance.
		pCell->custom_data["oncoprotein"] = 1.0;
		pCell->custom_data["car_antigen"] = antigen;
	}
	return;
}
"""

TUMOR_PHENOTYPE = r"""
void tumor_cell_phenotype_with_and_immune_stimulation(
	Cell* pCell, Phenotype& phenotype, double dt )
{
	static int cycle_start_index = live.find_phase_index( PhysiCell_constants::live );
	static int cycle_end_index = live.find_phase_index( PhysiCell_constants::live );
	static int oncoprotein_i = pCell->custom_data.find_variable_index( "oncoprotein" );
	static int antigen_i = pCell->custom_data.find_variable_index( "car_antigen" );
	static int immune_factor_index =
		microenvironment.find_density_index( "immunostimulatory factor" );

	phenotype.secretion.secretion_rates[immune_factor_index] = 10.0;
	update_cell_and_death_parameters_O2_based( pCell, phenotype, dt );

	if( phenotype.death.dead == true )
	{
		phenotype.secretion.secretion_rates[immune_factor_index] = 10.0;
		pCell->functions.update_phenotype = NULL;
		return;
	}

	// Repeated CAR engagement can select or induce an antigen-low remnant.
	if( pCell->state.number_of_attached_cells() > 0 )
	{
		double antigen_loss_rate = parameters.doubles( "antigen_loss_rate" );
		pCell->custom_data[antigen_i] *= exp( -antigen_loss_rate * dt );
		if( pCell->custom_data[antigen_i] < 0.0 )
		{ pCell->custom_data[antigen_i] = 0.0; }
	}

	phenotype.cycle.data.transition_rate( cycle_start_index, cycle_end_index )
		*= pCell->custom_data[oncoprotein_i];
	return;
}
"""

IMMUNE_MOTILITY = r"""
void immune_cell_motility( Cell* pCell, Phenotype& phenotype, double dt )
{
	static int immune_factor_index =
		microenvironment.find_density_index( "immunostimulatory factor" );
	static int exhaustion_i = pCell->custom_data.find_variable_index( "exhaustion" );

	double exhaustion = pCell->custom_data[exhaustion_i];
	double floor = parameters.doubles( "motility_exhaustion_floor" );
	double activity = 1.0 - exhaustion;
	if( activity < floor )
	{ activity = floor; }
	phenotype.motility.migration_speed =
		parameters.doubles( "immune_base_speed" ) * activity;

	if( pCell->state.attached_cells.size() == 0 )
	{
		phenotype.motility.is_motile = true;
		phenotype.motility.migration_bias_direction =
			pCell->nearest_gradient( immune_factor_index );
		normalize( &( phenotype.motility.migration_bias_direction ) );
	}
	else
	{
		phenotype.motility.is_motile = false;
	}
	return;
}
"""

ATTACHMENT = r"""
bool immune_cell_attempt_attachment( Cell* pAttacker, Cell* pTarget, double dt )
{
	static Cell_Definition* pTumor = find_cell_definition( "cancer cell" );
	static int antigen_i = pTarget->custom_data.find_variable_index( "car_antigen" );
	static int attach_rate_i =
		pAttacker->custom_data.find_variable_index( "attachment_rate" );
	static int contact_events_i =
		pAttacker->custom_data.find_variable_index( "contact_events" );

	if( pTarget->type != pTumor->type || pTarget->phenotype.death.dead == true )
	{ return false; }

	double threshold = pAttacker->custom_data["car_antigen_threshold"];
	double saturation = pAttacker->custom_data["car_antigen_saturation"];
	double antigen = pTarget->custom_data[antigen_i];
	if( antigen <= threshold )
	{ return false; }

	double max_distance = pAttacker->custom_data["max_attachment_distance"];
	double min_distance = pAttacker->custom_data["min_attachment_distance"];
	std::vector<double> displacement = pTarget->position - pAttacker->position;
	double distance = norm( displacement );
	if( distance > max_distance )
	{ return false; }

	double antigen_scale = ( antigen - threshold ) /
		( saturation - threshold + 1e-15 );
	if( antigen_scale > 1.0 )
	{ antigen_scale = 1.0; }
	if( antigen_scale < 0.0 )
	{ antigen_scale = 0.0; }

	double distance_scale = ( max_distance - distance ) /
		( max_distance - min_distance + 1e-15 );
	if( distance_scale > 1.0 )
	{ distance_scale = 1.0; }
	if( distance_scale < 0.0 )
	{ distance_scale = 0.0; }

	double hazard = pAttacker->custom_data[attach_rate_i]
		* antigen_scale * distance_scale;
	if( UniformRandom() < 1.0 - exp( -hazard * dt ) )
	{
		attach_cells( pAttacker, pTarget );
		pAttacker->custom_data[contact_events_i] += 1.0;
		return true;
	}
	return false;
}
"""

APOPTOSIS = r"""
bool immune_cell_attempt_apoptosis( Cell* pAttacker, Cell* pTarget, double dt )
{
	static int antigen_i = pTarget->custom_data.find_variable_index( "car_antigen" );
	static int kill_rate_i = pAttacker->custom_data.find_variable_index( "kill_rate" );
	static int exhaustion_i = pAttacker->custom_data.find_variable_index( "exhaustion" );
	static int kills_i = pAttacker->custom_data.find_variable_index( "kills" );

	double threshold = pAttacker->custom_data["car_antigen_threshold"];
	double saturation = pAttacker->custom_data["car_antigen_saturation"];
	double antigen = pTarget->custom_data[antigen_i];
	if( antigen <= threshold )
	{ return false; }

	double antigen_scale = ( antigen - threshold ) /
		( saturation - threshold + 1e-15 );
	if( antigen_scale > 1.0 )
	{ antigen_scale = 1.0; }
	if( antigen_scale < 0.0 )
	{ antigen_scale = 0.0; }

	double exhaustion = pAttacker->custom_data[exhaustion_i];
	double floor = parameters.doubles( "kill_exhaustion_floor" );
	double functional_fraction = floor + ( 1.0 - floor ) * ( 1.0 - exhaustion );
	double hazard = pAttacker->custom_data[kill_rate_i]
		* antigen_scale * functional_fraction;

	if( UniformRandom() < 1.0 - exp( -hazard * dt ) )
	{
		pAttacker->custom_data[kills_i] += 1.0;
		return true;
	}
	return false;
}
"""

IMMUNE_RULE = r"""
void immune_cell_rule( Cell* pCell, Phenotype& phenotype, double dt )
{
	static int attach_lifetime_i =
		pCell->custom_data.find_variable_index( "attachment_lifetime" );
	static int exhaustion_i =
		pCell->custom_data.find_variable_index( "exhaustion" );
	static int contact_minutes_i =
		pCell->custom_data.find_variable_index( "contact_minutes" );
	static int oxygen_i = microenvironment.find_density_index( "oxygen" );

	if( phenotype.death.dead == true )
	{
		pCell->functions.custom_cell_rule = NULL;
		return;
	}

	bool attached = pCell->state.number_of_attached_cells() > 0;
	double oxygen = pCell->nearest_density_vector()[oxygen_i];
	double hypoxia_threshold = parameters.doubles( "hypoxia_threshold" );
	double hypoxia = 0.0;
	if( oxygen < hypoxia_threshold )
	{
		hypoxia = ( hypoxia_threshold - oxygen ) /
			( hypoxia_threshold + 1e-15 );
	}

	double exhaustion = pCell->custom_data[exhaustion_i];
	double drive = parameters.doubles( "exhaustion_hypoxia_rate" ) * hypoxia;
	if( attached )
	{
		drive += parameters.doubles( "exhaustion_contact_rate" );
		pCell->custom_data[contact_minutes_i] += dt;
	}
	double recovery = attached ? 0.0 :
		parameters.doubles( "exhaustion_recovery_rate" ) * exhaustion;
	exhaustion += dt * ( drive * ( 1.0 - exhaustion ) - recovery );
	if( exhaustion < 0.0 )
	{ exhaustion = 0.0; }
	if( exhaustion > 1.0 )
	{ exhaustion = 1.0; }
	pCell->custom_data[exhaustion_i] = exhaustion;

	if( attached )
	{
		bool detach_me = false;
		Cell* pTarget = pCell->state.attached_cells[0];

		if( immune_cell_attempt_apoptosis( pCell, pTarget, dt ) )
		{
			immune_cell_trigger_apoptosis( pCell, pTarget );
			detach_me = true;
		}
		if( UniformRandom() <
			1.0 - exp( -dt / ( pCell->custom_data[attach_lifetime_i] + 1e-15 ) ) )
		{ detach_me = true; }

		if( detach_me )
		{
			detach_cells( pCell, pTarget );
			phenotype.motility.is_motile = true;
		}
		return;
	}

	if( immune_cell_check_neighbors_for_attachment( pCell, dt ) )
	{
		phenotype.motility.is_motile = false;
		return;
	}
	phenotype.motility.is_motile = true;
	return;
}
"""

SUMMARY_CODE = r"""
	// Compact endpoint and cell-resolved output for the Synthetic Lab adapter.
	Cell_Definition* pTumor = find_cell_definition( "cancer cell" );
	Cell_Definition* pImmune = find_cell_definition( "immune cell" );
	double tumor_radius = parameters.doubles( "tumor_radius" );
	double antigen_threshold = parameters.doubles( "antigen_threshold" );

	int tumor_total_cells = 0;
	int tumor_viable_cells = 0;
	int tumor_apoptotic_cells = 0;
	int tumor_necrotic_cells = 0;
	int antigen_low_viable_cells = 0;
	int immune_cells = 0;
	int infiltrating_immune_cells = 0;
	int exhausted_immune_cells = 0;
	int engaged_immune_cells = 0;
	double total_contacts = 0.0;
	double total_kills = 0.0;
	double viable_antigen_sum = 0.0;
	double tumor_oxygen_sum = 0.0;
	double exhaustion_sum = 0.0;
	double infiltration_depth_sum = 0.0;
	double max_infiltration_depth = 0.0;
	double radial_extent = 0.0;

	std::string cells_path = PhysiCell_settings.folder + "/cells.csv";
	std::ofstream cells_file( cells_path.c_str() );
	cells_file << "cell_type,x_um,y_um,z_um,dead,apoptotic,necrotic,"
		<< "car_antigen,oxygen_mmhg,exhaustion,engaged,contact_events,kills\n";

	for( int i = 0; i < all_cells->size(); i++ )
	{
		Cell* pCell = (*all_cells)[i];
		double dead = get_single_signal( pCell, "dead" );
		double apoptotic = get_single_signal( pCell, "apoptotic" );
		double necrotic = get_single_signal( pCell, "necrotic" );
		double oxygen = get_single_signal( pCell, "oxygen" );
		double antigen = 0.0;
		double exhaustion = 0.0;
		double contacts = 0.0;
		double kills = 0.0;
		int cell_type = -1;

		double radius = sqrt(
			pCell->position[0] * pCell->position[0] +
			pCell->position[1] * pCell->position[1] +
			pCell->position[2] * pCell->position[2] );

		if( pCell->type == pTumor->type )
		{
			cell_type = 0;
			antigen = pCell->custom_data["car_antigen"];
			tumor_total_cells++;
			tumor_oxygen_sum += oxygen;
			double extent = radius + pCell->phenotype.geometry.radius;
			if( extent > radial_extent )
			{ radial_extent = extent; }

			if( apoptotic > 0.5 )
			{ tumor_apoptotic_cells++; }
			else if( necrotic > 0.5 )
			{ tumor_necrotic_cells++; }
			else if( dead < 0.5 )
			{
				tumor_viable_cells++;
				viable_antigen_sum += antigen;
				if( antigen < antigen_threshold )
				{ antigen_low_viable_cells++; }
			}
		}
		else if( pCell->type == pImmune->type )
		{
			cell_type = 1;
			exhaustion = pCell->custom_data["exhaustion"];
			contacts = pCell->custom_data["contact_events"];
			kills = pCell->custom_data["kills"];
			immune_cells++;
			exhaustion_sum += exhaustion;
			total_contacts += contacts;
			total_kills += kills;
			if( exhaustion > 0.7 )
			{ exhausted_immune_cells++; }
			if( pCell->state.number_of_attached_cells() > 0 )
			{ engaged_immune_cells++; }
			double depth = tumor_radius - radius;
			if( depth >= 0.0 )
			{
				infiltrating_immune_cells++;
				infiltration_depth_sum += depth;
				if( depth > max_infiltration_depth )
				{ max_infiltration_depth = depth; }
			}
		}
		else
		{ continue; }

		cells_file << cell_type << "," << pCell->position[0] << ","
			<< pCell->position[1] << "," << pCell->position[2] << ","
			<< (dead > 0.5) << "," << (apoptotic > 0.5) << ","
			<< (necrotic > 0.5) << "," << antigen << "," << oxygen << ","
			<< exhaustion << ","
			<< (pCell->state.number_of_attached_cells() > 0) << ","
			<< contacts << "," << kills << "\n";
	}
	cells_file.close();

	double tumor_denominator = tumor_total_cells > 0 ? tumor_total_cells : 1;
	double viable_denominator = tumor_viable_cells > 0 ? tumor_viable_cells : 1;
	double immune_denominator = immune_cells > 0 ? immune_cells : 1;
	double infiltrating_denominator =
		infiltrating_immune_cells > 0 ? infiltrating_immune_cells : 1;

	std::string summary_path = PhysiCell_settings.folder + "/summary.csv";
	std::ofstream summary_file( summary_path.c_str() );
	summary_file
		<< "tumor_total_cells,tumor_viable_cells,tumor_apoptotic_cells,"
		<< "tumor_necrotic_cells,antigen_low_viable_cells,immune_cells,"
		<< "infiltrating_immune_cells,exhausted_immune_cells,"
		<< "engaged_immune_cells,total_contacts,total_kills,"
		<< "mean_viable_antigen,mean_tumor_oxygen_mmhg,mean_exhaustion,"
		<< "mean_infiltration_depth_um,max_infiltration_depth_um,"
		<< "equivalent_diameter_um\n";
	summary_file
		<< tumor_total_cells << "," << tumor_viable_cells << ","
		<< tumor_apoptotic_cells << "," << tumor_necrotic_cells << ","
		<< antigen_low_viable_cells << "," << immune_cells << ","
		<< infiltrating_immune_cells << "," << exhausted_immune_cells << ","
		<< engaged_immune_cells << "," << total_contacts << ","
		<< total_kills << "," << viable_antigen_sum / viable_denominator << ","
		<< tumor_oxygen_sum / tumor_denominator << ","
		<< exhaustion_sum / immune_denominator << ","
		<< infiltration_depth_sum / infiltrating_denominator << ","
		<< max_infiltration_depth << "," << 2.0 * radial_extent << "\n";
	summary_file.close();

"""


def replace_once(text, old, new, path):
    if text.count(old) != 1:
        raise RuntimeError(f"Expected one patch point in {path}: {old!r}")
    return text.replace(old, new, 1)


def replace_function(text, signature, next_signature, replacement, path):
    start = text.find(signature)
    end = text.find(next_signature, start + len(signature))
    if start < 0 or end < 0:
        raise RuntimeError(
            f"Could not replace function in {path}: {signature!r} -> {next_signature!r}"
        )
    return text[:start] + replacement.strip() + "\n\n" + text[end:]


def prepare(root):
    root = root.resolve()
    subprocess.run(["make", "cancer-immune-sample"], cwd=root, check=True)

    makefile = root / "Makefile"
    text = makefile.read_text(encoding="utf-8")
    text = replace_once(
        text,
        "PROGRAM_NAME := cancer_immune_3D",
        "PROGRAM_NAME := car_t_spheroid",
        makefile,
    )
    makefile.write_text(text, encoding="utf-8")

    custom = root / "custom_modules" / "cancer_immune_3D.cpp"
    text = custom.read_text(encoding="utf-8")
    text = replace_function(
        text,
        "void introduce_immune_cells( void )",
        "std::vector<std::vector<double>> create_cell_sphere_positions",
        INTRODUCE_IMMUNE_CELLS,
        custom,
    )
    text = replace_function(
        text,
        "void setup_tissue( void )",
        "// custom cell phenotype function",
        SETUP_TISSUE,
        custom,
    )
    text = replace_function(
        text,
        "void tumor_cell_phenotype_with_and_immune_stimulation(",
        "std::vector<std::string> cancer_immune_coloring_function",
        TUMOR_PHENOTYPE,
        custom,
    )
    text = replace_function(
        text,
        "void immune_cell_motility(",
        "Cell* immune_cell_check_neighbors_for_attachment",
        IMMUNE_MOTILITY,
        custom,
    )
    text = replace_function(
        text,
        "bool immune_cell_attempt_attachment(",
        "bool immune_cell_attempt_apoptosis(",
        ATTACHMENT,
        custom,
    )
    text = replace_function(
        text,
        "bool immune_cell_attempt_apoptosis(",
        "bool immune_cell_trigger_apoptosis(",
        APOPTOSIS,
        custom,
    )
    text = replace_function(
        text,
        "void immune_cell_rule(",
        "void adhesion_contact_function(",
        IMMUNE_RULE,
        custom,
    )
    custom.write_text(text, encoding="utf-8")

    main = root / "main.cpp"
    text = main.read_text(encoding="utf-8")
    text = replace_once(
        text,
        "\n\treturn 0; \n}",
        "\n" + SUMMARY_CODE + "\treturn 0; \n}",
        main,
    )
    main.write_text(text, encoding="utf-8")

    print(f"Prepared PhysiCell CAR-T spheroid project in {root}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("physicell_root", type=Path)
    args = parser.parse_args()
    prepare(args.physicell_root)


if __name__ == "__main__":
    main()
