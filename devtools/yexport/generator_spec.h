#pragma once

#include "attribute.h"
#include "std_helpers.h"
#include "diag/exception.h"

#include <util/generic/hash.h>
#include <util/generic/hash_set.h>
#include <util/generic/serialized_enum.h>
#include <util/string/cast.h>
#include <contrib/libs/toml11/toml/value.hpp>
#include <contrib/libs/jinja2cpp/include/jinja2cpp/value.h>
#include "generator_spec_enum.h"

#include <filesystem>
#include <string>
#include <vector>
#include <iosfwd>

namespace NYexport {

struct TTemplateSpec {
    fs::path Template;
    std::string ResultName;

    bool operator== (const TTemplateSpec&) const noexcept = default;
};

struct TCopySpec {
    THashMap<ECopyLocation, THashSet<fs::path>> Items;

    bool Useless() const;
    void Append(const TCopySpec& copySpec);

    bool operator== (const TCopySpec&) const noexcept = default;
};

struct TTargetSpec {
    bool IsExtraTarget{false};///< This target is extra, must be without templates
    bool IsTest{false};///< Used only with ExtraTarget == true! This target is test
    std::vector<TTemplateSpec> Templates = {};///< Templates (only for main targets)
    std::vector<TTemplateSpec> MergePlatformTemplates = {};///< Templates for merge platforms (must be same count as Templates)
    TCopySpec Copy;///< Lists for copy files

    bool operator==(const TTargetSpec&) const noexcept = default;
};

struct TGeneratorRule {
    TCopySpec Copy;
    THashSet<std::string> AttrNames;
    THashSet<std::string> PlatformNames;
    THashMap<std::string, TVector<std::string>> AddValues; //TODO: Proper values instead of std::string

    bool Useless() const;
    bool operator== (const TGeneratorRule&) const noexcept = default;
};

using TAttrGroup = THashMap<TAttr, EAttrTypes>;
using TAttrGroups = THashMap<EAttrGroup, TAttrGroup>;

struct TGeneratorSpec {
    using TRuleSet = THashSet<const TGeneratorRule*>;

    TTargetSpec Root;///< Root of export for one platform
    THashMap<std::string, TTargetSpec> Targets;///< Targets in directory by name
    jinja2::ValuesMap Platforms;
    TAttrGroups AttrGroups;
    THashMap<std::string, TVector<uint32_t>> AttrToRuleIds;
    THashMap<std::string, TVector<uint32_t>> PlatformToRuleIds;
    THashMap<std::string, TVector<fs::path>> Merge;
    THashMap<uint32_t, TGeneratorRule> Rules;
    bool UseManagedPeersClosure{false};
    bool IgnorePlatforms{false};

    TRuleSet GetAttrRules(const std::string_view attr) const;
    TRuleSet GetPlatformRules(const std::string_view platform) const;
};

struct TBadGeneratorSpec: public TYExportException {
    TBadGeneratorSpec(const std::string& msg)
        : TYExportException{msg}
    {}
    TBadGeneratorSpec(std::string&& msg)
        : TYExportException{std::move(msg)}
    {}
    TBadGeneratorSpec() = default;
};

namespace NGeneratorSpecError {
    constexpr const char* WrongFieldType = "Wrong field type";
    constexpr const char* MissingField = "Missing field";
    constexpr const char* SpecificationError = "Specification error";
    constexpr const char* UnknownField = "Unknown field";
}

TGeneratorSpec ReadGeneratorSpec(const fs::path& path);
TGeneratorSpec ReadGeneratorSpec(std::istream& input, const fs::path& path);

}
