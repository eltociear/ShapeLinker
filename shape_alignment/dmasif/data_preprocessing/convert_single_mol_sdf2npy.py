import numpy as np
from pathlib import Path
from tqdm import tqdm
from rdkit import Chem
from rdkit.Chem import AllChem
from shape_alignment.dmasif.data_preprocessing import chem_utils

ele2num = {"C": 0, "C1": 0, "H": 1, "O": 2, "N": 3, "S": 4, "SE": 5, "other": 6, "filler": 7}


def get_conformers_and_atoms(sdf_file_path, torsion_noise=0):
    with Chem.SDMolSupplier(sdf_file_path) as suppl:
        for m in suppl:
            if m is None: 
                continue
            m.GetNumAtoms()
            break

    if torsion_noise > 0:
        chem_utils.add_noise_to_torsion_angles(m, deg=torsion_noise)
    for mol in m.GetConformers():
        conformer_coords = mol.GetPositions().copy()
        atom_types = [x.GetSymbol() for x in m.GetAtoms()]
        assert len(atom_types) == conformer_coords.shape[0]
        yield atom_types, conformer_coords


def load_sdf_np(sdf_file_path, center, torsion_noise=0):
    """Loads a .ply mesh to return a point cloud and connectivity."""
    # Load the data

    conformer_nps = []

    for atom_names, coords in get_conformers_and_atoms(sdf_file_path, torsion_noise=0):
        conformer_nps.append(mol_to_np(atom_names, coords, center))

    return conformer_nps


def mol_to_np(atom_names, coords, center):
    types_array = np.zeros((len(atom_names), len(set(list(ele2num.values())))))
    for i, name in enumerate(atom_names):
        if name in ele2num:
            types_array[i, ele2num[name]] = 1.
        else:
            types_array[i, ele2num["other"]] = 1.
    if center:
        coords = coords - np.mean(coords, axis=0, keepdims=True)
    return {"xyz": coords, "types": types_array}


def convert_smiles(smiles_list, num_conformers, npy_dir, torsion_noise=0):
    print("Converting PDBs")
    npy_dir = Path(npy_dir)
    for smiles in tqdm(smiles_list):
        conformer_nps = load_sdf_np(smiles, num_conformers, center=False)
        for i, conformer in enumerate(conformer_nps):
            np.save(npy_dir / f"{smiles}_{i}_atomxyz.npy", conformer["xyz"])
            np.save(npy_dir / f"{smiles}_{i}_atomtypes.npy", conformer["types"])