# frozen_string_literal: true
require "minitest/autorun"
require "tmpdir"
require "fileutils"
require_relative "site_contract"

class SiteContractTest < Minitest::Test
  def write(relative, text)
    file = File.join(@root, relative)
    FileUtils.mkdir_p(File.dirname(file))
    File.write(file, text)
  end

  def page(name, route, body, extra = "")
    write("_pages/#{name}.md", "---\nlayout: #{name == 'cv' ? 'cv' : 'page'}\npermalink: #{route}\n#{extra}---\n#{body}")
  end

  def document(body)
    %(<html><head><link rel="stylesheet" href="/assets/css/tailwind.css"></head><body><nav id="navbar"></nav><main>#{body}</main></body></html>)
  end

  def setup
    @root = Dir.mktmpdir("site-contract-", ENV.fetch("TMPDIR"))
    @config = {
      "url" => "https://example.test", "baseurl" => "", "include" => ["_pages"],
      "exclude" => SiteContract::PRIVATE_PATHS + ["_site"], "theme" => "al_folio_core",
      "plugins" => SiteContract::REQUIRED_PLUGINS,
      "third_party_libraries" => %w[fontawesome academicons scholar-icons].to_h { |name| [name, { "integrity" => { "css" => "sha384-fixture" } }] },
      "collections" => { "news" => { "output" => false } },
      "scholar" => { "source" => "_bibliography", "bibliography" => "papers.bib", "query" => "@*" }
    }
    write("_config.yml", @config.to_yaml)
    write("Gemfile", %w[al_folio_core al_folio_cv al_icons al_math].map { |name| "gem '#{name}', '= 1.0.0'" }.join("\n"))
    write("_bibliography/papers.bib", "@article{fixture, title={A title}, author={Author, A}, year={2001}}")
    write("_data/cv.yml", { "cv" => { "name" => "Fixture Person", "label" => "Researcher", "email" => "test@example.test",
                                      "sections" => { "Education" => [{ "institution" => "Fixture University" }] } } }.to_yaml)
    page("home", "/", '<a href="/members/">Members</a>', "announcements:\n  enabled: false\n")
    page("cv", "/cv/", "Curriculum vitae")
    page("profiles", "/members/", <<~MD)
      <div class="bics-roster" markdown="1">

      | Name | Research |
      | :--- | :--- |
      | <img class="bics-member-photo" src="/assets/photo.svg" alt="Fixture Person">Fixture Person | Circuits |

      </div>
    MD
    page("papers", "/publications/", "{% bibliography %}")
    page("news", "/news/", "hidden", "published: false\n")
    write("_site/index.html", document('<a href="/members/">Members</a><img src="/assets/photo.svg" alt="Person">'))
    write("_site/members/index.html", document('<div class="bics-roster"><table><tbody><tr><td><img class="bics-member-photo" src="/assets/photo.svg" alt="Fixture Person">Fixture Person</td><td>Circuits</td></tr></tbody></table></div>'))
    write("_site/cv/index.html", document('<div class="cv">Fixture Person Researcher test@example.test Education Fixture University</div>'))
    write("_site/publications/index.html", document('<ol class="bibliography"><li><div id="fixture"><div class="title">A title</div></div></li></ol>'))
    write("_site/assets/photo.svg", '<svg xmlns="http://www.w3.org/2000/svg"/>')
    write("_site/assets/css/tailwind.css", '.fixed-top{position:fixed;padding:calc(var(--spacing)*2)}')
    write("_site/assets/css/main.css", '.navbar-toggler{color:red}.bics-brand{display:flex}')
  end

  def teardown
    FileUtils.remove_entry(@root) # Only this test's generated fixture.
  end

  def errors
    SiteContract.new(@root).output(File.join(@root, "_site"))
  end

  def assert_failure(fragment)
    result = errors
    assert result.any? { |message| message.include?(fragment) }, "Expected #{fragment.inspect}, got #{result.inspect}"
  end

  def test_valid_consumer_site
    assert_empty errors
  end

  def test_intentional_override_is_allowed
    write("_includes/header.liquid", "consumer navigation")
    assert_empty errors
  end

  def test_unexpected_override_is_caught
    write("_includes/forbidden.liquid", "vendored runtime")
    assert_failure "Forbidden theme/runtime override"
  end

  def test_missing_asset_is_caught
    write("_site/index.html", document('<img src="/assets/missing.jpg">'))
    assert_failure "Missing local link/asset"
  end

  def test_broken_public_route_is_caught
    page("new", "/new/", "New page")
    assert_failure "Missing public route /new/"
  end

  def test_broken_internal_link_is_caught
    write("_site/index.html", document('<a href="/does-not-exist/">Broken link</a>'))
    assert_failure "Missing local link/asset"
  end

  def test_same_origin_absolute_link_and_fragment_are_checked
    write("_site/index.html", document('<a href="https://example.test/members/#missing">Broken anchor</a>'))
    assert_failure "Broken local fragment"
  end

  def test_relative_and_encoded_assets_resolve
    write("_site/assets/space name.svg", "<svg/>")
    write("_site/index.html", document('<a href="members/">Members</a><img src="assets/space%20name.svg">'))
    assert_empty errors
  end

  def test_baseurl_links_resolve
    @config["baseurl"] = "/lab"
    write("_config.yml", @config.to_yaml)
    Dir.glob(File.join(@root, "_site/**/*.html")).each do |file|
      File.write(file, File.read(file).gsub('href="/', 'href="/lab/').gsub('src="/', 'src="/lab/'))
    end
    assert_empty errors
  end

  def test_nested_internal_document_leak_is_caught
    write("_site/design/private/index.html", document("private"))
    assert_failure "Internal document leaked"
  end

  def test_rendered_harness_leak_is_caught
    write("_site/CLAUDE.html", document("internal"))
    assert_failure "Internal document leaked"
  end

  def test_internal_exclusion_cannot_be_removed
    @config["exclude"].delete("test")
    write("_config.yml", @config.to_yaml)
    assert_failure "Internal path must be excluded"
  end

  def test_duplicate_publication_is_caught
    original = File.read(File.join(@root, "_bibliography/papers.bib"))
    write("_bibliography/papers.bib", original + "\n" + original)
    assert_failure "Duplicate BibTeX identifiers"
  end

  def test_same_line_duplicate_bibtex_identifiers_are_caught
    write("_bibliography/papers.bib", "@article{same, title={Title}, author={Author}, year={2000}} @article{same, title={Other}, author={Author}, year={2001}}")
    assert_failure "Duplicate BibTeX identifiers"
  end

  def test_missing_css_and_navbar_are_caught
    write("_site/index.html", "<html><body><main>Home</main></body></html>")
    assert_failure "Navigation absent"
    assert_failure "Tailwind stylesheet not linked"
  end

  def test_css_asset_reference_is_checked
    write("_site/assets/css/main.css", '.navbar-toggler{}.bics-brand{background:url(../missing.svg)}')
    assert_failure "Missing local link/asset"
  end

  def test_public_collection_route_is_derived
    @config["collections"]["projects"] = { "output" => true, "permalink" => "/projects/:name/" }
    write("_config.yml", @config.to_yaml)
    write("_projects/new.md", "---\ntitle: A project\n---\nNew project")
    assert_failure "Missing public route /projects/new/"
    write("_site/projects/new/index.html", document("New project"))
    assert_empty errors
  end

  def test_external_resources_are_not_scraped
    write("_site/index.html", document('<a href="https://outside.example/missing">External</a><img src="data:image/svg+xml,fixture">'))
    assert_empty errors
  end

  def test_site_origin_without_trailing_slash_resolves
    write("_site/index.html", document('<a href="https://example.test">Home</a>'))
    assert_empty errors
  end

  def test_wrong_rendered_publication_is_caught
    write("_site/publications/index.html", document('<ol class="bibliography"><li><div id="other"><div class="title">Other</div></div></li></ol>'))
    assert_failure "Rendered publication identifiers differ"
  end

  def test_changed_member_data_is_caught
    write("_site/members/index.html", document('<div class="bics-roster"><table><tbody><tr><td>Somebody Else</td></tr></tbody></table></div>'))
    assert_failure "Rendered member roster differs"
  end

  def test_broken_markdown_region_is_caught_even_when_alumni_table_renders
    broken = <<~MD
      <div class="bics-roster" aria-label="Current" markdown="1">

      <!-- prettier-ignore -->
      | Name | Research |
      | :--- | :--- |
      | Fixture Person | Circuits |

      </div>

      <div class="bics-roster" aria-label="Alumni" markdown="1">

      | Name | Degree |
      | :--- | :--- |
      | Previous Person | M.S. |

      </div>
    MD
    page("profiles", "/members/", broken)
    require "kramdown"
    require "kramdown-parser-gfm"
    # Reproduce the old blind spot: both source-render and output lose Current's
    # table, while their aggregate comparison still sees the same Alumni row.
    rendered = Kramdown::Document.new(broken, input: "GFM").to_html
    fragment = Nokogiri::HTML.fragment(rendered)
    assert_equal 0, fragment.css('.bics-roster[aria-label="Current"] table').length
    assert_equal 1, fragment.css('.bics-roster[aria-label="Alumni"] tbody tr').length
    write("_site/members/index.html", document(rendered))
    assert_failure "Roster Current must render one HTML table"
  end

  def test_range_ignore_preserves_liquid_table_through_locked_formatter
    safe = <<~MD
      <!-- prettier-ignore-start -->

      <div class="bics-roster" aria-label="Current" markdown="1">

      | Name | Research |
      | :--- | :--- |
      | <img class="bics-member-photo" src="{{ '/assets/photo.svg' | relative_url }}" alt="Fixture Person">Fixture Person | Circuits |

      </div>

      <!-- prettier-ignore-end -->
    MD
    require "open3"
    formatter = File.expand_path("../node_modules/prettier/bin/prettier.cjs", __dir__)
    formatted, status = Open3.capture2("node", formatter, "--stdin-filepath", "_pages/profiles.md", stdin_data: safe)
    assert status.success?, "locked formatter failed"
    assert_equal safe, formatted, "formatter changed protected roster source"
    page("profiles", "/members/", formatted)
    require "kramdown"
    require "kramdown-parser-gfm"
    # Jekyll evaluates the literal Liquid asset URL before its Markdown pass.
    expanded = formatted.gsub(/\{\{.*?\}\}/, "/assets/photo.svg")
    rendered = Kramdown::Document.new(expanded, input: "GFM").to_html
    assert_equal 1, Nokogiri::HTML.fragment(rendered).css(".bics-roster table tbody tr").length
    write("_site/members/index.html", document(rendered))
    assert_empty errors
  end

  def test_roster_header_and_separator_columns_must_agree
    source = File.read(File.join(@root, "_pages/profiles.md"))
    write("_pages/profiles.md", source.sub("| :--- | :--- |", "| :--- | :--- | --- |"))
    assert_failure "source header/separator column count differs"
  end

  def test_roster_source_data_row_count_is_independent_of_renderer
    page("profiles", "/members/", <<~MD)
      <div class="bics-roster" aria-label="Current" markdown="1">

      | Name | Research |
      | :--- | :--- |
      | First Person | Circuits |
      | Second Person | Systems |

      </div>
    MD
    write("_site/members/index.html", document('<div class="bics-roster" aria-label="Current"><table><thead><tr><th>Name</th><th>Research</th></tr></thead><tbody><tr><td>First Person</td><td>Circuits</td></tr></tbody></table></div>'))
    assert_failure "Roster Current source has 2 data rows, rendered table has 1"
  end

  def test_cv_data_must_render
    write("_site/cv/index.html", document('<div class="cv">Researcher</div>'))
    assert_failure "CV name absent"
  end

  def test_unpublished_news_does_not_render
    write("_site/news/index.html", document("news"))
    assert_failure "Unpublished page leaked"
    assert_failure "Disabled News collection leaked"
  end

  def test_production_css_corruption_is_caught
    write("_site/assets/css/tailwind.css", '.fixed-top{position:fixed;margin:calc(var( -  - spacing)*2)}')
    assert_failure "Corrupted production CSS"
  end

  def test_manifest_is_derived_from_new_source_page
    page("new", "/new/", "New page")
    write("_site/new/index.html", document("New page"))
    manifest = File.join(@root, "manifest.json")
    assert_empty SiteContract.new(@root).output(File.join(@root, "_site"), manifest: manifest)
    assert_includes JSON.parse(File.read(manifest))["pages"].map { |page| page["route"] }, "/new/"
  end
end
