import os
import numpy as np
import tqdm

import reinvent_models.reinvent_core.models.model as reinvent

from running_modes.constructors.base_running_mode import BaseRunningMode
from running_modes.configurations.general_configuration_envelope import GeneralConfigurationEnvelope
from running_modes.configurations.compound_sampling.sample_from_model_configuration import SampleFromModelConfiguration
from running_modes.sampling.logging.sampling_logger import SamplingLogger

VALID_SAMPLING_MODES = ['multinomial', 'top_k', 'top_p', 'top_k_top_p']

class SampleFromModelRunner(BaseRunningMode):

    def __init__(self, main_config: GeneralConfigurationEnvelope, configuration: SampleFromModelConfiguration):
        self._model = reinvent.Model.load_from_file(configuration.model_path, sampling_mode=True)
        self._output = self._open_output(path=configuration.output_smiles_path)
        self._num_smiles = configuration.num_smiles
        self._batch_size = configuration.batch_size
        self._with_likelihood = configuration.with_likelihood
        self._sampling_mode = configuration.sampling_mode
        self._temperature = configuration.temperature
        self._k = configuration.k
        self._p = configuration.p
        if self._p != 1.0:
            raise NotImplementedError("top_p sampling is not yet implemented")
        if self._sampling_mode not in VALID_SAMPLING_MODES:
            raise ValueError(f"{self._sampling_mode} is invalid. Sampling mode must be one of {VALID_SAMPLING_MODES}")
        self._logger = SamplingLogger(main_config)

    def _open_output(self, path):
        try:
            os.mkdir(os.path.dirname(path))
        except FileExistsError:
            pass
        return open(path, "wt+")

    def run(self):
        molecules_left = self._num_smiles
        totalsmiles = []
        totallikelihoods = []
        with tqdm.tqdm(total=self._num_smiles) as progress_bar:
            while molecules_left > 0:
                current_batch_size = min(self._batch_size, molecules_left)
                smiles, likelihoods = self._model.sample_smiles(current_batch_size, batch_size=self._batch_size, 
                                                        sampling_type = self._sampling_mode, k=self._k, p=self._p, temperature=self._temperature)
                totalsmiles.extend(smiles)
                totallikelihoods.extend(likelihoods)

                for smi, log_likelihood in zip(smiles, likelihoods):
                    output_row = [smi]
                    if self._with_likelihood:
                        output_row.append("{}".format(log_likelihood))
                    self._output.write("{}\n".format("\t".join(output_row)))

                molecules_left -= current_batch_size

                progress_bar.update(current_batch_size)

            self._logger.timestep_report(np.asarray(totalsmiles), np.asarray(totallikelihoods))
        self._output.close()
        self._logger.log_out_input_configuration()
