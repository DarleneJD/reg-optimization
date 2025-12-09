############################################################
# Julia script: Daily PF + tap change counting with PMD
############################################################

using PowerModelsDistribution
using JSON   # for optional pretty printing of solution (debug)

# ---------------------------------------------------------
# User configuration
# ---------------------------------------------------------

# Path to your master DSS file (same as in your Python code)
const DSS_FILE = "IEEE13_v1.dss"

# Names of the voltage regulators we care about (case-insensitive)
const REGULATOR_NAMES = Set(["REG1", "REG2", "REG3"])

# ---------------------------------------------------------
# Helper: parse DSS as multinetwork daily time series
# ---------------------------------------------------------

"""
    parse_daily_multinetwork(dss_file::String)

Parses a DSS feeder into the PowerModelsDistribution ENGINEERING
data model, expanding daily time-series data into a multinetwork
structure (one network per time step, similar to OpenDSS `mode=daily`).
"""
function parse_daily_multinetwork(dss_file::String)
    data_eng = PowerModelsDistribution.parse_file(
        dss_file;
        data_model   = PowerModelsDistribution.ENGINEERING,
        multinetwork = true,
        time_series  = "hourly",   # use 'daily' loadshape/time-series from DSS
    )
    return data_eng
end

# ---------------------------------------------------------
# Helper: run native unbalanced PF for all time steps
# ---------------------------------------------------------

"""
    run_daily_power_flow!(data_eng)

Runs the native unbalanced AC power flow (`compute_mc_pf`) on the
multinetwork engineering model.

Returns the full result dictionary (with `result["solution"]` etc.).
"""
function run_daily_power_flow!(data_eng::Dict{String,Any})
    # The native PF is OpenDSS-like and can work directly from the
    # ENGINEERING model with `multinetwork=true`.
    pf_result = PowerModelsDistribution.compute_mc_pf(
        data_eng;
        multinetwork = true,
        verbose      = false
    )

    if pf_result["termination_status"] != "LOCALLY_SOLVED"
        @warn "Power flow did not converge with status $(pf_result["termination_status"])"
    end

    return pf_result
end

# ---------------------------------------------------------
# Helper: extract regulator taps from one network solution
# ---------------------------------------------------------

"""
    extract_reg_taps(nw_solution) -> Dict{String, Vector{Float64}}

Extracts tap positions for REG1/REG2/REG3 from the solution
of a single network (one time step).

This function is written defensively because the exact key
names for tap variables depend on the PMD version and problem
type. Adjust this after you inspect your own `pf_result`.
"""
function extract_reg_taps(nw_solution::Dict{String,Any})
    taps = Dict{String, Vector{Float64}}()

    # In PMD solutions, transformer-related values usually
    # live under "transformer" in each network.
    haskey(nw_solution, "transformer") || return taps
    trsol = nw_solution["transformer"]

    for (tr_name, tr_data_any) in trsol
        # Filter by regulator IDs (case-insensitive)
        if !(uppercase(tr_name) in REGULATOR_NAMES)
            continue
        end

        tr_data = tr_data_any::Dict{String,Any}

        # Heuristics for tap field names:
        #  - "tm" is common for per-phase tap ratios
        #  - "tap" sometimes appears as a single scalar
        #  - you may need to adjust this depending on your PMD version
        if haskey(tr_data, "tm")
            # assume it's an array or something indexable
            tm_val = tr_data["tm"]
            # normalize to Vector{Float64}
            taps[tr_name] = [Float64(v) for v in tm_val]
        elseif haskey(tr_data, "tap")
            taps[tr_name] = [Float64(tr_data["tap"])]
        else
            # no recognizable tap field; skip
            @warn "No 'tm' or 'tap' field in transformer solution for $tr_name"
        end
    end

    return taps
end

# ---------------------------------------------------------
# Helper: count tap changes over all time steps
# ---------------------------------------------------------

"""
    count_tap_changes(solution_nw) -> Int

`solution_nw` is expected to be `pf_result["solution"]["nw"]`, i.e.
a dictionary of per-time-step solutions (indexed as "1","2",...).

We call `extract_reg_taps` for each time step and count how many
times any regulator tap value changes compared to the previous
time step. Each per-phase change is counted as one tap operation.
"""
function count_tap_changes(solution_nw::Dict{String,Any}; atol::Float64 = 1e-6)
    # Sort network IDs numerically: "1","2","3",...
    nw_ids = sort(collect(keys(solution_nw))) do s
        parse(Int, s)
    end

    prev_taps::Union{Dict{String, Vector{Float64}}, Nothing} = nothing
    total_changes = 0

    for nw_id_str in nw_ids
        nw_sol = solution_nw[nw_id_str]::Dict{String,Any}
        curr_taps = extract_reg_taps(nw_sol)

        if prev_taps !== nothing
            # compare current vs previous taps regulator by regulator
            for (name, curr_vec) in curr_taps
                if haskey(prev_taps, name)
                    prev_vec = prev_taps[name]
                    n = min(length(curr_vec), length(prev_vec))
                    for k in 1:n
                        if !isapprox(curr_vec[k], prev_vec[k]; atol=atol)
                            total_changes += 1
                        end
                    end
                end
            end
        end

        prev_taps = curr_taps
    end

    return total_changes
end

# ---------------------------------------------------------
# Main: put everything together
# ---------------------------------------------------------

function main()
    println("Parsing DSS file as daily multinetwork: ")
    println("  $DSS_FILE")

    data_eng = parse_daily_multinetwork(DSS_FILE)

    println("Running daily native power flow with compute_mc_pf...")
    pf_result = run_daily_power_flow!(data_eng)

    solution = pf_result["solution"]
    haskey(solution, "nw") || error("Expected multinetwork solution under key \"nw\"")

    tap_changes = count_tap_changes(solution["nw"])

    println()
    println("==============================================")
    println("  Daily PF finished with native solver")
    println("  Total tap changes for REG1/2/3 = $tap_changes")
    println("==============================================")

    # OPTIONAL: uncomment to inspect the structure once
    # open("pf_solution_debug.json", "w") do io
    #     JSON.print(io, pf_result; 4)
    # end
    # println("Solution structure dumped to pf_solution_debug.json for inspection.")
end

# ---------------------------------------------------------
# Run when executed as a script
# ---------------------------------------------------------

if abspath(PROGRAM_FILE) == @__FILE__
    main()
end
