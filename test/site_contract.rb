# frozen_string_literal: true

# Consumer checks for this lab site, shared by local checks and deployment CI.
require "bibtex"
require "date"
require "json"
require "nokogiri"
require "optparse"
require "pathname"
require "uri"
require "yaml"
require "jekyll"

class SiteContract
  # These are intentional consumer customizations. New theme overrides require
  # an explicit review of this list; vendored layouts/runtime remain forbidden.
  OVERRIDES = %w[_includes/header.liquid _sass/_bics.scss _sass/_bics_research.scss assets/css/main.scss].freeze
  RUNTIME_TREES = %w[_includes _layouts _sass _plugins _scripts assets/tailwind assets/webfonts assets/fonts assets/js assets/css].freeze
  PRIVATE_PATHS = %w[design output .gh .claude .codex test bin docs .project-status.md AGENTS.md CLAUDE.md
                     UPSTREAM_AGENTS.md UPSTREAM_CLAUDE.md requirements-cv.txt SITE_MAINTENANCE.md].freeze
  REQUIRED_PLUGINS = %w[al_folio_core al_folio_cv al_icons al_math jekyll/scholar].freeze

  attr_reader :errors, :config

  def initialize(root)
    @root = File.expand_path(root)
    @errors = []
    @config = yaml("_config.yml")
  end

  def yaml(file)
    value = YAML.safe_load(File.read(File.join(@root, file)), permitted_classes: [Date, Time], aliases: true)
    raise "#{file} must contain a mapping" unless value.is_a?(Hash)
    value
  end

  def fail_if(condition, message)
    @errors << message if condition
  end

  def files_under(relative)
    Dir.glob(File.join(@root, relative, "**", "*"), File::FNM_DOTMATCH)
       .select { |file| File.file?(file) }.map { |file| Pathname(file).relative_path_from(Pathname(@root)).to_s }
  end

  def excluded?(path)
    Array(@config["exclude"]).any? do |entry|
      entry = entry.to_s.delete_suffix("/")
      path == entry || path.start_with?(entry + "/") || File.fnmatch?(entry, path, File::FNM_PATHNAME | File::FNM_DOTMATCH)
    end
  end

  def pages
    @pages ||= begin
      # Jekyll owns route calculation and front-matter defaults. Do not maintain
      # a second hardcoded route/name/year/count manifest for the public pages.
      site = Jekyll::Site.new(Jekyll.configuration("source" => @root, "quiet" => true))
      paths = Dir.glob(File.join(@root, "_pages", "**", "*.{md,html,markdown}")) +
              Dir.glob(File.join(@root, "*.{md,html,markdown}"))
      result = paths.filter_map do |file|
        relative = Pathname(file).relative_path_from(Pathname(@root)).to_s
        next if excluded?(relative) || !File.read(file).start_with?("---")
        next if relative.start_with?("_pages/") && !Array(@config["include"]).include?("_pages")
        page = Jekyll::Page.new(site, @root, File.dirname(relative), File.basename(relative))
        { "source" => relative, "route" => page.url, "data" => page.data,
          "content" => page.content, "published" => page.data["published"] != false }
      end
      site.collections.each_value do |collection|
        collection.read
        collection.docs.each do |doc|
          relative = doc.relative_path.delete_prefix("/")
          next if excluded?(relative)
          result << { "source" => relative, "route" => doc.url, "data" => doc.data,
                      "content" => doc.content, "published" => doc.write? }
        end
      end
      result
    end
  end

  def public_pages
    pages.select { |page| page["published"] }
  end

  def publications
    @publications ||= begin
      scholar = @config.fetch("scholar")
      source = scholar.fetch("source").delete_prefix("/")
      file = File.join(@root, source, scholar.fetch("bibliography"))
      raw = File.read(file).sub(/\A---\s*\n.*?^---\s*\n/m, "")
      # The parser renames duplicate keys. Its lexer preserves original KEY
      # tokens, including same-line entries, and ignores keys inside comments.
      lexer = BibTeX::Lexer.new
      lexer.analyse(raw)
      keys = []
      loop do
        type, value = lexer.next_token
        break unless type
        keys << value if type == :KEY
      end
      duplicates = keys.tally.select { |_, count| count > 1 }.keys
      fail_if(!duplicates.empty?, "Duplicate BibTeX identifiers: #{duplicates.join(', ')}")
      bibliography = BibTeX.parse(raw)
      fail_if(bibliography.errors?, "BibTeX parse errors: #{bibliography.errors.map(&:to_s).join('; ')}")
      entries = bibliography.data.select { |entry| entry.is_a?(BibTeX::Entry) }
      duplicates = entries.group_by(&:key).select { |_, group| group.length > 1 }.keys
      fail_if(!duplicates.empty?, "Duplicate BibTeX identifiers: #{duplicates.join(', ')}")
      fail_if(entries.empty?, "Publication bibliography has no entries")
      entries.each do |entry|
        %i[title author year].each do |field|
          fail_if(entry[field].to_s.strip.empty?, "Publication #{entry.key} is missing #{field}")
        end
      end
      entries
    end
  end

  def cv
    @cv ||= yaml("_data/cv.yml").fetch("cv")
  end

  def source
    fail_if(@config["theme"] != "al_folio_core", "Theme must remain wired to al_folio_core")
    REQUIRED_PLUGINS.each do |plugin|
      fail_if(!Array(@config["plugins"]).include?(plugin), "Missing configured plugin: #{plugin}")
    end
    gemfile = File.read(File.join(@root, "Gemfile"))
    %w[al_folio_core al_folio_cv al_icons al_math].each do |gem_name|
      fail_if(!gemfile.match?(/gem\s+['"]#{Regexp.escape(gem_name)}['"],\s*['"]=\s*\d+\.\d+\.\d+['"]/), "Gemfile must pin released #{gem_name}")
    end
    %w[fontawesome academicons scholar-icons].each do |library|
      integrity = @config.dig("third_party_libraries", library, "integrity", "css")
      fail_if(!integrity.to_s.match?(/\Asha(?:256|384|512)-\S+\z/), "Missing icon stylesheet SRI: #{library}")
    end
    RUNTIME_TREES.each do |directory|
      files_under(directory).each do |file|
        fail_if(!OVERRIDES.include?(file), "Forbidden theme/runtime override: #{file}")
      end
    end
    %w[tailwind.config.js assets/fonts/academicons.woff assets/fonts/academicons.ttf
       assets/fonts/scholar-icons.woff assets/fonts/scholar-icons.ttf].each do |file|
      fail_if(File.exist?(File.join(@root, file)), "Forbidden theme/runtime override: #{file}")
    end
    PRIVATE_PATHS.each do |path|
      fail_if(!excluded?(path), "Internal path must be excluded from Jekyll output: #{path}")
    end
    fail_if(public_pages.empty?, "No public page routes discovered")
    public_pages.group_by { |page| page["route"] }.each do |route, group|
      fail_if(group.length > 1, "Duplicate public route #{route}: #{group.map { |page| page['source'] }.join(', ')}")
    end
    publications
    fail_if(!cv.is_a?(Hash), "CV data must contain a cv mapping")
    %w[name label email].each { |field| fail_if(cv[field].to_s.strip.empty?, "CV missing #{field}") }
    sections = cv["sections"]
    fail_if(!sections.is_a?(Hash) || sections.empty?, "CV sections must be a nonempty mapping")
    if sections.is_a?(Hash)
      sections.each do |name, entries|
        fail_if(!entries.is_a?(Array) || entries.empty? || entries.any? { |entry| !entry.is_a?(Hash) || entry.empty? },
                "CV section #{name} must contain nonempty entry mappings")
      end
    end
    fail_if(public_pages.none? { |page| page["data"]["layout"] == "cv" }, "No public CV page")
    members = public_pages.find { |page| page["source"] == "_pages/profiles.md" }
    fail_if(members.nil? || !members["content"].include?("bics-roster"), "Members source must contain the public roster")
    @errors
  end

  def normalized(text)
    # Kramdown smart quotes and BibTeX whitespace should not make data snapshots.
    Nokogiri::HTML.fragment(text.to_s).text.tr("‘’“”", "''\"\"").gsub(/\s+/, " ").strip
  end

  def output_path(route)
    route = URI::DEFAULT_PARSER.unescape(route.to_s.split(/[?#]/, 2).first || "/")
    path = File.expand_path(route.delete_prefix("/"), @output)
    return nil unless path == @output || path.start_with?(@output + "/")
    path = File.join(path, "index.html") if File.directory?(path) || route.end_with?("/")
    File.file?(path) ? path : nil
  end

  def html(file)
    @documents[file] ||= Nokogiri::HTML(File.read(file))
  end

  def local_target(value, from)
    return if value.nil? || value.strip.empty? || value == "#"
    value = value.strip
    encoded = URI::DEFAULT_PARSER.escape(value, /[^A-Za-z0-9\-._~:\/?#\[\]@!$&'()*+,;=%]/)
    uri = URI.parse(encoded)
    return if uri.scheme && !%w[http https].include?(uri.scheme)
    site_uri = URI.parse(@config.fetch("url"))
    return if uri.host && uri.host != site_uri.host
    current = "/" + Pathname(from).relative_path_from(Pathname(@output)).to_s
    uri = URI.join("https://#{site_uri.host}#{current}", encoded)
    route = uri.path
    baseurl = @config["baseurl"].to_s.delete_suffix("/")
    if !baseurl.empty?
      unless route == baseurl || route.start_with?(baseurl + "/")
        @errors << "Local link outside configured baseurl in #{current}: #{value}"
        return
      end
      route = route.delete_prefix(baseurl)
      route = "/" if route.empty?
    end
    target = output_path(route)
    fail_if(target.nil?, "Missing local link/asset in #{current}: #{value}")
    return unless target && uri.fragment && !uri.fragment.empty? && File.extname(target) == ".html"
    fragment = URI::DEFAULT_PARSER.unescape(uri.fragment)
    found = html(target).xpath("//*[@id or @name]").any? { |node| node["id"] == fragment || node["name"] == fragment }
    fail_if(!found, "Broken local fragment in #{current}: #{value}")
  rescue URI::InvalidURIError => exc
    @errors << "Invalid local URL in #{from}: #{value} (#{exc.message})"
  end

  def check_links(file)
    document = html(file)
    document.css("[href], [src], [poster], object[data]").each do |node|
      %w[href src poster].each { |attr| local_target(node[attr], file) if node[attr] }
      local_target(node["data"], file) if node.name == "object"
    end
    document.css("[srcset]").each do |node|
      next if node["srcset"].start_with?("data:")
      node["srcset"].split(",").each { |entry| local_target(entry.strip.split(/\s+/).first, file) }
    end
    fail_if(document.at_css("[role='main'], main").nil?, "No main content landmark: #{file}") if public_pages.any? { |page| output_path(page["route"]) == file }
  end

  def check_css
    %w[tailwind main].each do |name|
      file = output_path("/assets/css/#{name}.css")
      fail_if(file.nil? || File.size(file).zero?, "Missing/empty production stylesheet: #{name}.css")
      next unless file
      css = File.read(file)
      fail_if(css.include?("var( -  - "), "Corrupted production CSS custom property in #{name}.css")
      if name == "tailwind"
        fail_if(!css.include?("var(--spacing)"), "Tailwind spacing tokens missing")
        fail_if(!css.match?(/\.fixed-top[^{}]*\{[^}]*position:\s*fixed/), "Tailwind fixed navbar rule missing")
      else
        fail_if(!css.include?("navbar-toggler") || !css.include?("bics-brand"), "Consumer navbar styling missing from main.css")
      end
    end
    Dir.glob(File.join(@output, "**", "*.css")).each do |file|
      File.read(file).scan(/url\(\s*['"]?([^)'"\s]+)['"]?\s*\)/).flatten.each { |url| local_target(url, file) }
    end
  end

  def check_roster_tables(content, actual)
    # Inspect raw Markdown rows independently of Kramdown. A shared Markdown
    # parser failure must not make broken source and broken output agree.
    regions = content.scan(/<div\b([^>]*)>(.*?)<\/div>/m).filter_map do |attributes, body|
      node = Nokogiri::HTML.fragment("<div #{attributes}></div>").at_css("div")
      next unless node["class"].to_s.split.include?("bics-roster")
      [node, body]
    end
    rendered_regions = actual.css(".bics-roster")
    fail_if(regions.empty? || regions.length != rendered_regions.length,
            "Roster region count differs between source and rendered page")
    regions.each_with_index do |(source_region, body), index|
      label = source_region["aria-label"] || "region #{index + 1}"
      # Liquid filter pipes are not Markdown cell separators.
      lines = body.gsub(/\{\{.*?\}\}/m, "LIQUID_VALUE").lines
      pipe_rows = lines.select { |line| line.match?(/^\s*\|/) }.map do |line|
        line.strip.delete_prefix("|").delete_suffix("|").split(/(?<!\\)\|/, -1).map(&:strip)
      end
      separator = pipe_rows.index { |row| !row.empty? && row.all? { |cell| cell.match?(/\A:?-+:?\z/) } }
      if separator.nil? || separator.zero?
        @errors << "Roster #{label} source must contain a Markdown table header and separator"
        next
      end
      expected_rows = pipe_rows.drop(separator + 1)
      columns = pipe_rows[separator - 1].length
      fail_if(pipe_rows[separator].length != columns,
              "Roster #{label} source header/separator column count differs")
      fail_if(expected_rows.empty? || expected_rows.any? { |row| row.length != columns },
              "Roster #{label} source has empty or inconsistent data rows")
      region = rendered_regions[index]
      next unless region
      fail_if(region["aria-label"] != source_region["aria-label"], "Roster #{label} rendered region label differs from source")
      tables = region.css("table")
      fail_if(tables.length != 1, "Roster #{label} must render one HTML table (found #{tables.length})")
      next unless tables.length == 1
      rows = tables.first.css("tbody > tr")
      fail_if(rows.length != expected_rows.length,
              "Roster #{label} source has #{expected_rows.length} data rows, rendered table has #{rows.length}")
      fail_if(rows.any? { |row| row.css("td").length != columns },
              "Roster #{label} rendered table cell count differs from source")
    end
  end

  def check_rendered_data
    publication_page = public_pages.find { |page| page["content"].match?(/\{%\s*bibliography\s*%\}/) }
    fail_if(publication_page.nil?, "No public full bibliography page")
    if publication_page && (file = output_path(publication_page["route"]))
      rendered = html(file).css("ol.bibliography > li [id]").select { |node| node.at_css(".title") }.map { |node| node["id"] }
      # Use the configured scholar query, the same selection as {% bibliography %}.
      bibliography = BibTeX::Bibliography.new
      publications.each { |entry| bibliography << entry.dup }
      expected = bibliography.query(@config.dig("scholar", "query") || "@*").map(&:key)
      fail_if(rendered.sort != expected.sort, "Rendered publication identifiers differ from bibliography (missing #{(expected - rendered).join(', ')}, extra #{(rendered - expected).join(', ')})")
      fail_if(rendered.uniq.length != rendered.length, "Duplicate rendered publication identifiers")
    end
    public_pages.select { |page| page["data"]["selected_papers"] }.each do |page|
      next unless (file = output_path(page["route"]))
      rendered = html(file).css("ol.bibliography > li [id]").select { |node| node.at_css(".title") }.map { |node| node["id"] }
      expected = publications.select { |entry| entry[:selected].to_s == "true" }.map(&:key)
      fail_if(rendered.sort != expected.sort, "Selected publications differ from source: #{page['route']}")
    end
    cv_page = public_pages.find { |page| page["data"]["layout"] == "cv" }
    if cv_page && (file = output_path(cv_page["route"]))
      text = normalized(html(file).at_css(".cv")&.text)
      %w[name label email].each { |field| fail_if(!text.include?(normalized(cv[field])), "CV #{field} absent from rendered page") }
      cv.fetch("sections", {}).each do |section, entries|
        fail_if(!text.include?(normalized(section)), "CV section absent from rendered page: #{section}")
        entries.each do |entry|
          %w[label institution company title].each do |key|
            fail_if(entry[key] && !text.include?(normalized(entry[key])), "CV #{section} entry absent from rendered page: #{entry[key]}")
          end
        end
      end
    end
    members = public_pages.find { |page| page["source"] == "_pages/profiles.md" }
    if members && (file = output_path(members["route"]))
      # Render source Markdown without evaluating Liquid; compare text, not counts.
      require "kramdown"
      require "kramdown-parser-gfm"
      expected = Nokogiri::HTML.fragment(Kramdown::Document.new(members["content"].gsub(/\{\{\s*['"]([^'"]+)['"]\s*\|\s*relative_url\s*\}\}/) { @config["baseurl"].to_s + Regexp.last_match(1) }, input: "GFM").to_html)
      actual = html(file)
      check_roster_tables(members["content"], actual)
      wanted = expected.css(".bics-roster tbody tr").map { |row| row.css("td").map { |cell| normalized(cell.text) } }
      got = actual.css(".bics-roster tbody tr").map { |row| row.css("td").map { |cell| normalized(cell.text) } }
      fail_if(wanted.empty? || wanted != got, "Rendered member roster differs from source")
      expected.css("img.bics-member-photo").each do |img|
        fail_if(img["alt"].to_s.strip.empty?, "Member photo missing descriptive alt text")
        fail_if(actual.css("img.bics-member-photo").none? { |node| node["alt"] == img["alt"] }, "Member photo absent from render: #{img['alt']}")
      end
    end
  end

  def output(directory, manifest: nil)
    @output = File.expand_path(directory)
    @documents = {}
    source
    return @errors unless @errors.empty?
    fail_if(!File.directory?(@output), "Built output not found: #{@output}")
    return @errors unless File.directory?(@output)
    public_pages.each do |page|
      fail_if(output_path(page["route"]).nil?, "Missing public route #{page['route']} from #{page['source']}")
    end
    pages.reject { |page| page["published"] }.each do |page|
      fail_if(!output_path(page["route"]).nil?, "Unpublished page leaked: #{page['route']}")
    end
    Dir.glob(File.join(@output, "**", "*"), File::FNM_DOTMATCH).select { |file| File.file?(file) }.each do |file|
      relative = Pathname(file).relative_path_from(Pathname(@output)).to_s
      components = relative.split("/")
      stem = File.basename(relative, File.extname(relative))
      internal = PRIVATE_PATHS.any? { |path| relative == path || relative.start_with?(path + "/") || stem == File.basename(path, File.extname(path)) } ||
                 components.any? { |part| part.match?(/\A(?:UPSTREAM_|CLAUDE|AGENTS|requirements(?:-|\.))/) }
      fail_if(internal, "Internal document leaked into built output: #{relative}")
      fail_if(excluded?(relative), "Excluded source path leaked into built output: #{relative}")
    end
    if @config.dig("collections", "news", "output") == false
      fail_if(Dir.glob(File.join(@output, "news", "**", "*")).any? { |file| File.file?(file) }, "Disabled News collection leaked into output")
    end
    Dir.glob(File.join(@output, "**", "*.html")).each { |file| check_links(file) }
    public_pages.each do |page|
      next unless (file = output_path(page["route"]))
      document = html(file)
      fail_if(document.at_css("#navbar").nil?, "Navigation absent from #{page['route']}")
      if page.dig("data", "announcements", "enabled") == false
        fail_if(!document.at_css(".news").nil?, "Disabled announcements rendered on #{page['route']}")
      end
      styles = document.css("link[rel='stylesheet']").map { |node| node["href"].to_s.split("?").first }
      fail_if(styles.none? { |url| url.end_with?("/assets/css/tailwind.css") }, "Tailwind stylesheet not linked: #{page['route']}")
      compat = @config.dig("al_folio", "compat", "bootstrap", "enabled") == true
      fail_if(styles.any? { |url| url.end_with?("/bootstrap-compat.css") } != compat, "Bootstrap compatibility stylesheet disagrees with config: #{page['route']}")
      fail_if(!compat && document.css("script[src]").any? { |node| node['src'].match?(/jquery/i) }, "Unexpected jQuery runtime: #{page['route']}")
    end
    check_css
    check_rendered_data
    if manifest && @errors.empty?
      File.write(manifest, JSON.pretty_generate({ "baseurl" => @config["baseurl"].to_s, "pages" => public_pages.map { |page| page.slice("source", "route") },
                                                "navigation" => public_pages.select { |page| page['data']['nav'] }.map { |page| page.slice("source", "route") },
                                                "publications" => publications.map(&:key) }) + "\n")
    end
    @errors
  end
end

if $PROGRAM_NAME == __FILE__
  options = { root: File.expand_path("..", __dir__), output: "_site" }
  parser = OptionParser.new do |cli|
    cli.banner = "Usage: bundle exec ruby test/site_contract.rb source|output [--root PATH] [--output PATH] [--manifest PATH]"
    cli.on("--root PATH") { |value| options[:root] = value }
    cli.on("--output PATH") { |value| options[:output] = value }
    cli.on("--manifest PATH") { |value| options[:manifest] = value }
  end
  begin
    parser.parse!
    mode = ARGV.shift
    raise OptionParser::InvalidArgument, "expected source or output" unless %w[source output].include?(mode) && ARGV.empty?
    contract = SiteContract.new(options[:root])
    mode == "source" ? contract.source : contract.output(File.expand_path(options[:output], options[:root]), manifest: options[:manifest])
    if contract.errors.empty?
      puts "[site] #{mode} consumer contract passed"
    else
      warn "[site] #{mode} consumer contract failed (#{contract.errors.length}):"
      contract.errors.uniq.each { |message| warn "- #{message}" }
      exit 1
    end
  rescue StandardError => exc
    warn "[site] ERROR: #{exc.class}: #{exc.message}"
    exit 1
  end
end
