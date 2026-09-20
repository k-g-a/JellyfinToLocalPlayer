-- ############### Configurable options below ###############

-- The etlp install directory. Note the trailing slash, and all slashes must be "/".
local etlp_root_dir = "C:/Green/etlp-python-embed-win32/"

-- If not using python_embed, change this to the absolute path of your own python and install the requests dependency.
local etlp_python = etlp_root_dir .. "python_embed/python.exe"

-- Do not modify the following three lines.
local etlp_util_dir = etlp_root_dir .. "utils/"
local etlp_bgm_sync_py = etlp_util_dir .. "bangumi_sync.py"
local etlp_trakt_sync_py = etlp_util_dir .. "trakt_sync.py"

-- List of enabled scripts. Delete any you do not want; remember to delete the comma too.
-- Remember to also edit etlp ini config to enable per domain, so all are enabled here by default.
local enable_srcipts = { etlp_bgm_sync_py, etlp_trakt_sync_py }

-- ############### Configurable options above ###############

local script_run = false
local is_url = false
local my_unpack = table.unpack or unpack

local function sleep(secs)
    local t0 = mp.get_time()
    while mp.get_time() - t0 < secs do end
end

local function check_is_url(path)
    return string.match(path, "^https?://") ~= nil
end

local function check_progress_and_domain()
    local percent_pos = mp.get_property_number("percent-pos", 0)

    if is_url and not script_run and percent_pos >= 90 then
        local path = mp.get_property("path", "")
        local title = mp.get_property("media-title", "")
        mp.msg.info(etlp_python)
        for _, script_path in ipairs(enable_srcipts) do
            local run_command = { etlp_python, script_path, path }
            mp.msg.info(script_path .. "  -->  " .. title)
            mp.command_native_async({"run", my_unpack(run_command)}, function(success, result, error)
                if not success then
                    mp.msg.error("Failed to run Python script: " ..
                        script_path .. ", error: " .. (error or "unknown error") .. "\n" .. table.concat(run_command, " "))
                end
            end)
            sleep(0.1)
        end
        script_run = true
    end
end

local function on_start_file()
    local path = mp.get_property("path", "")
    is_url = check_is_url(path)
    script_run = false
    mp.msg.info("Starting new file, resetting script run status.")
end

mp.register_event("start-file", on_start_file)

mp.add_periodic_timer(1, check_progress_and_domain)
