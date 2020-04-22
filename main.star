#!/usr/bin/env lucicfg generate

# This is the main entry point for the generation of configuration.
# Invoking (lucicfg is included with depot_tools):
# lucicfg generate ./main.star
# will update the configuration in the generated/ directory.


# Load and register protos.
load("@stdlib//internal/descpb.star", "wellknown_descpb")
protos = proto.new_descriptor_set(
    name = "chromiumos",
    blob = io.read_file("metadata/proto/descpb.bin"),
    deps = [wellknown_descpb],
)
protos.register()


# Load test metadata.
load("//metadata/metadata.star", "METADATA")


# Generate metadata output.
def _generate(config):
    """
    Serializes a proto message to files.

    A text proto and binary proto are written.
    """
    def _generate_impl(ctx):
        ctx.output["config.cfg"] = proto.to_textpb(config)
        ctx.output["config.binaryproto"] = proto.to_wirepb(config)

    lucicfg.generator(impl = _generate_impl)

_generate(METADATA)



