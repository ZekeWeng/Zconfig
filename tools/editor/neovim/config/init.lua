-- Bootstrap lazy.nvim — commit kept in sync with lazy-lock.json
local lazypath = vim.fn.stdpath("data") .. "/lazy/lazy.nvim"
local lazy_sha = "306a05526ada86a7b30af95c5cc81ffba93fef97"
if not vim.loop.fs_stat(lazypath) then
  vim.fn.system({
    "git", "clone", "--filter=blob:none",
    "https://github.com/folke/lazy.nvim.git", lazypath,
  })
  vim.fn.system({ "git", "-C", lazypath, "checkout", lazy_sha })
end
vim.opt.rtp:prepend(lazypath)

-- Load configuration
require("config.options")
require("config.keymaps")
require("config.autocmds")

-- Setup lazy.nvim
require("lazy").setup("plugins")
