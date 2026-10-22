function run_kssolv_job(kssolvRoot, jobDir)
% User's SCF -> rho -> options.NSCF -> eband sequence, with numeric export.
oldDir = pwd;
cleanupDir = onCleanup(@() cd(oldDir));
diary(fullfile(jobDir,'matlab.log'));
cleanupDiary = onCleanup(@() diary('off'));
cd(kssolvRoot);
if exist('KSSOLV3.prj', 'file')
    openProject('KSSOLV3.prj');
else
    KSSOLV.startup();
end
addpath(jobDir);
cleanupPath = onCleanup(@() rmpath(jobDir));
cfg = jsondecode(fileread(fullfile(jobDir, 'config.json')));
assert(~isempty(regexp(cfg.structure_function, '^mpstruct_[0-9a-f]{16}$', 'once')));
pseudopotential.PpType('default');
crystal = feval(cfg.structure_function);
crystal.ecut = cfg.parameters.ecut;
crystal.autokpts = [reshape(cfg.parameters.mesh,1,[]) 0 0 0];
crystal.nbnd = cfg.parameters.nbnd;
crystal.smear = cfg.parameters.smear;
crystal.funct = cfg.parameters.functional;
cd(jobDir);
set(groot, 'defaultFigureVisible', 'off');
fprintf('KSSOLV job: SCF starts\n');
[crystal, H, ~, scfInfo] = scf(crystal);
assert(isnumeric(H.rho) && ~isempty(H.rho) && all(isfinite(H.rho(:))), 'Invalid SCF density');
scfSummary = struct('converged',logical(scfInfo.converge), ...
    'iterations',numel(scfInfo.SCFerrvec),'final_residual',scfInfo.SCFerrvec(end), ...
    'total_energy_hartree',scfInfo.Etot,'fermi_energy_hartree',scfInfo.Efermi);
writeJson(fullfile(jobDir,'scf_info.json'),scfSummary);
save(fullfile(jobDir, 'scf_state.mat'), 'crystal', 'H', 'scfInfo', '-v7.3');
assert(scfInfo.converge, 'SCF did not converge; no NSCF will be performed');
export_kssolv_bands(crystal,H,cfg,jobDir,scfSummary);
end

function writeJson(path, data)
fid=fopen(path,'w','n','UTF-8');
assert(fid~=-1,'Cannot write result JSON');
cleanup=onCleanup(@() fclose(fid));
fprintf(fid,'%s',jsonencode(data));
end
