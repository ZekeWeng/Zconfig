-- Bootstrap lazy.nvim — pinned to stable @ 2026-04-22
local lazypath = vim.fn.stdpath("data") .. "/lazy/lazy.nvim"
local lazy_sha = "332b4cbc8bf61589b6ff58ce42fca80173154669"
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
