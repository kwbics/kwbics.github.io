# frozen_string_literal: true

# Consumer cache key for main.css.
#
# The installed theme's bust_css_cache hashes only the theme gem's Sass, so an
# edit to this site's _sass partials or assets/css/main.scss left main.css?v=
# unchanged and returning visitors kept stale CSS. This keeps the upstream
# version and folds in this site's Sass sources, read from the site of the
# current Liquid render. bust_file_cache is untouched.
require "digest/md5"
require "pathname"
require "jekyll-cache-bust"

module BicsCacheBust
  MAIN_ENTRY = "assets/css/main.scss"

  module_function

  # [[path relative to the site source, absolute path], ...] sorted by relative path.
  def local_sources(site)
    source = File.expand_path(site.source)
    sass = site.config["sass"]
    sass_dir = File.expand_path((sass.is_a?(Hash) && sass["sass_dir"]) || "_sass", source)
    partials = Dir.glob("**/*", base: sass_dir).map { |relative| File.join(sass_dir, relative) }
    (partials + [File.join(source, MAIN_ENTRY)])
      .select { |path| File.file?(path) }
      .map { |path| [Pathname(path).relative_path_from(Pathname(source)).to_s, path] }
      .sort_by(&:first)
  end

  def version(upstream_version, site)
    digest = Digest::MD5.new
    digest << upstream_version << "\0"
    local_sources(site).each do |relative, path|
      bytes = File.binread(path)
      digest << relative << "\0" << bytes.bytesize.to_s << "\0" << bytes
    end
    digest.hexdigest
  end

  module Filter
    def bust_css_cache(file_name)
      upstream = super
      site = @context && @context.registers[:site]
      return upstream unless site

      prefix = "#{file_name}?v="
      unless upstream.start_with?(prefix)
        raise Jekyll::Errors::FatalException, "bics_cache_bust: unexpected bust_css_cache result #{upstream.inspect}"
      end

      prefix + BicsCacheBust.version(upstream.delete_prefix(prefix), site)
    end
  end
end

# Liquid already includes Jekyll::CacheBust in its strainer; Ruby >= 3.0
# propagates this prepend there, so no second filter registration is needed.
Jekyll::CacheBust.prepend(BicsCacheBust::Filter) unless Jekyll::CacheBust.ancestors.include?(BicsCacheBust::Filter)
