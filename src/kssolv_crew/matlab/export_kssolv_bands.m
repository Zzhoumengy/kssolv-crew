function export_kssolv_bands(crystal,H,cfg,jobDir,scfSummary)
% Same NSCF call, explicitly aligned to the SCF reference across all edges.
NSCFOptions = options.NSCF();
NSCFOptions.rho0 = H.rho;
NSCFOptions.verbose = "on";
scfKpts = crystal.kpts;
scfWks = crystal.wks;
scfFermi = scfSummary.fermi_energy_hartree;
for j = 1:numel(cfg.segments)
    seg = cfg.segments(j);
    pts = seg.points;
    labels = {strrep(char(seg.labels(1)),'\Gamma',char(915)), strrep(char(seg.labels(2)),'\Gamma',char(915))};
    kPoints = {pts(1,1),pts(1,2),pts(1,3),cfg.parameters.points_per_segment,labels{1}; ...
               pts(2,1),pts(2,2),pts(2,3),cfg.parameters.points_per_segment,labels{2}};
    crystal.kpts = scfKpts;
    crystal.wks = scfWks;
    fprintf('NSCF eband segment %d of %d\n',j,numel(cfg.segments));
    [nativeBands,kPointPath] = eband(crystal,NSCFOptions,kPoints);
    % Local eband subtracts the NSCF getocc Fermi energy, which differs per edge.
    nscfFermi = crystal.efermi;
    energyBands = nativeBands + (nscfFermi-scfFermi)*HARTREE2EV;
    assert(isnumeric(energyBands) && ~isempty(energyBands) && all(isfinite(energyBands(:))), 'Invalid band energies');
    assert(size(energyBands,1)==cfg.parameters.nbnd && size(energyBands,2)==size(kPointPath,1), 'Unexpected energy shape');
    cartK=kPointPath*(2*pi*inv(crystal.supercell)');
    distance=[0;cumsum(vecnorm(diff(cartK),2,2))];
    curves=struct('x',{},'y',{});
    for band=1:size(energyBands,1)
        curves(end+1)=struct('x',distance','y',energyBands(band,:)); %#ok<AGROW>
    end
    save(fullfile(jobDir,sprintf('plot_data_%03d.mat',j)),'curves','energyBands','nativeBands','kPointPath','distance','scfFermi','nscfFermi');
    data=struct('energy_units','eV relative to SCF Fermi level','energy_bands',energyBands, ...
        'k_fractional',kPointPath,'k_distance_inverse_bohr',distance,'labels',{labels}, ...
        'scf_fermi_hartree',scfFermi,'nscf_fermi_hartree',nscfFermi);
    writeJson(fullfile(jobDir,sprintf('band_data_%03d.json',j)),data);
    fig=figure('Visible','off','Color','w');
    plot(distance,energyBands','LineWidth',1);
    hold on;yline(0,'k--');hold off;
    xlim([distance(1),distance(end)]);xticks([distance(1),distance(end)]);xticklabels(labels);
    ylabel('Energy - E_F (eV)');xlabel('High-symmetry k path');
    title(sprintf('KSSOLV bands: segment %d',j));grid on;
    exportgraphics(fig,fullfile(jobDir,sprintf('band_%03d_01.png',j)));
    savefig(fig,fullfile(jobDir,sprintf('band_%03d_01.fig',j)));close(fig);
end
result=struct('scf_returned',true,'density_finite',true,'scf_converged',logical(scfSummary.converged), ...
    'scf',scfSummary,'segments',numel(cfg.segments),'convergence_verified',false, ...
    'energy_units','eV relative to SCF Fermi level','shared_fermi_reference',true, ...
    'band_gap',[],'matlab_version',version);
writeJson(fullfile(jobDir,'engine_result.json'),result);
end

function writeJson(path,data)
fid=fopen(path,'w','n','UTF-8');assert(fid~=-1,'Cannot write result JSON');
cleanup=onCleanup(@() fclose(fid));fprintf(fid,'%s',jsonencode(data));
end
