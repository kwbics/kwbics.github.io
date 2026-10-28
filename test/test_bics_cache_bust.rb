# frozen_string_literal: true
require "minitest/autorun"
require "minitest/mock"
require "tmpdir"
require "fileutils"
require "digest/md5"
require "jekyll"
require "jekyll-cache-bust"
require "al_folio_core"

plugin = [ENV["BICS_CACHE_BUST_PLUGIN"],
          File.expand_path("../_plugins/bics_cache_bust.rb", __dir__),
          File.expand_path("bics_cache_bust.rb", __dir__)].compact.find { |path| File.file?(path) }
raise "bics_cache_bust.rb not found" unless plugin

require plugin
Jekyll.logger.log_level = :error

class BicsCacheBustTest < Minitest::Test
  CSS = "{{ '/assets/css/main.css' | relative_url | bust_css_cache }}"
  JS = "{{ '/assets/js/common.js' | relative_url | bust_file_cache }}"
  CSS_URL = "/lab/assets/css/main.css"
  EMPTY = Digest::MD5.hexdigest("")

  def setup
    @tmp = Dir.mktmpdir("bics-cache-bust-", ENV.fetch("TMPDIR"))
  end

  def teardown
    FileUtils.rm_rf(@tmp)
  end

  def write(root, relative, text)
    path = File.join(root, relative)
    FileUtils.mkdir_p(File.dirname(path))
    File.binwrite(path, text)
  end

  def source(name, bics: "td { width: 25%; }\n")
    root = File.join(@tmp, name)
    write(root, "_sass/_bics.scss", bics)
    write(root, "assets/css/main.scss", "---\n---\n@use \"bics\";\n")
    root
  end

  def site(root, baseurl: "/lab")
    Jekyll::Site.new(Jekyll.configuration("source" => root, "destination" => File.join(root, "_site"),
                                          "baseurl" => baseurl, "url" => "https://example.test",
                                          "quiet" => true, "skip_config_files" => true))
  end

  def render(template, site)
    Liquid::Template.parse(template).render!({}, registers: { site: site }, strict_filters: true)
  end

  def upstream_version(url)
    Jekyll::CacheBust::CacheDigester.new(file_name: url, directory: "assets/_sass").digest!.delete_prefix("#{url}?v=")
  end

  # Specification: MD5(upstream version, then each local Sass source sorted by
  # relative path as "path NUL size NUL bytes").
  def expected(url, root, upstream = upstream_version(url))
    relatives = Dir.glob("**/*", base: File.join(root, "_sass")).map { |relative| "_sass/#{relative}" }
    relatives << "assets/css/main.scss"
    payload = relatives.select { |relative| File.file?(File.join(root, relative)) }.sort.map do |relative|
      bytes = File.binread(File.join(root, relative))
      "#{relative}\0#{bytes.bytesize}\0".b + bytes
    end
    "#{url}?v=#{Digest::MD5.hexdigest("#{upstream}\0".b + payload.join.b)}"
  end

  def test_upstream_version_is_retained_and_url_is_preserved
    root = source("a")
    { "/lab" => CSS_URL, "" => "/assets/css/main.css" }.each do |baseurl, url|
      refute_equal EMPTY, upstream_version(url), "theme Sass fallback is inactive"
      key = render(CSS, site(root, baseurl: baseurl))
      assert_equal expected(url, root), key

      fake = Object.new
      fake.define_singleton_method(:digest!) { "#{url}?v=0123456789abcdef0123456789abcdef" }
      stubbed = Jekyll::CacheBust::CacheDigester.stub(:new, fake) { render(CSS, site(root, baseurl: baseurl)) }
      assert_equal expected(url, root, "0123456789abcdef0123456789abcdef"), stubbed
      refute_equal key, stubbed
    end
  end

  def test_unchanged_sources_keep_the_same_key
    root = source("a")
    first = render(CSS, site(root))
    reused = site(root)
    assert_equal [first, first, first], [render(CSS, site(root)), render(CSS, reused), render(CSS, reused)]
  end

  def assert_byte_change_and_restore(relative)
    root = source("a")
    path = File.join(root, relative)
    bytes = File.binread(path)
    reused = site(root)
    original = render(CSS, reused)
    File.binwrite(path, bytes + " ")
    changed = render(CSS, reused)
    refute_equal original, changed
    assert_equal expected(CSS_URL, root), changed
    File.binwrite(path, bytes)
    assert_equal original, render(CSS, reused)
    assert_equal original, render(CSS, site(root))
  end

  def test_local_partial_byte_change_and_restore
    assert_byte_change_and_restore("_sass/_bics.scss")
  end

  def test_main_entry_byte_change_and_restore
    assert_byte_change_and_restore("assets/css/main.scss")
  end

  def test_new_nested_partial_changes_the_key
    root = source("a")
    original = render(CSS, site(root))
    write(root, "_sass/components/_roster.scss", ".roster { width: 100%; }\n")
    added = render(CSS, site(root))
    refute_equal original, added
    assert_equal expected(CSS_URL, root), added
    FileUtils.rm_f(File.join(root, "_sass/components/_roster.scss"))
    assert_equal original, render(CSS, site(root))
  end

  def test_two_sites_in_one_process_are_isolated
    first_root = source("a")
    second_root = source("b", bics: "td { width: 30%; }\n")
    first_site = site(first_root)
    second_site = site(second_root)
    first = render(CSS, first_site)
    second = render(CSS, second_site)
    refute_equal first, second
    assert_equal [expected(CSS_URL, first_root), expected(CSS_URL, second_root)], [first, second]
    assert_equal first, render(CSS, first_site)
    write(second_root, "_sass/_bics.scss", "td { width: 31%; }\n")
    assert_equal first, render(CSS, first_site)
    refute_equal second, render(CSS, second_site)
  end

  def test_file_cache_is_unchanged
    root = source("a")
    reused = site(root)
    url = "/lab/assets/js/common.js"
    before = render(JS, reused)
    assert_equal Jekyll::CacheBust::CacheDigester.new(file_name: url).digest!, before
    refute_equal "#{url}?v=#{EMPTY}", before
    write(root, "_sass/_bics.scss", "td { width: 40%; }\n")
    assert_equal before, render(JS, reused)
  end
end
